"""Experiment campaigns (pilot, controlled grid, size-up/Q1, final evaluation). Never run concurrently.

Every campaign: builds the list of Specs, shuffles them with a fixed seed inside the campaign (B0 reference runs
are forced first so that the equivalence reference exists), skips completed runs (resume), and prints a budget.
"""
from __future__ import annotations
import argparse, json, random
from pathlib import Path
import pandas as pd

from .config import load_config, resolve
from .runner import Spec, run_experiment, completed_ids
from .prepare import prepare_ukdale_lot, prepared_paths


def lots_of(cfg: dict, split: str) -> list[str]:
    s = json.loads((resolve(cfg, "manifests") / "splits.json").read_text())
    return [k for k, v in sorted(s.items(), key=lambda kv: kv[1]["source_gb"]) if v["split"] == split]


def split_of(cfg: dict, lot: str) -> str:
    if lot == "metropt3":
        return "n/a"
    return json.loads((resolve(cfg, "manifests") / "splits.json").read_text())[lot]["split"]


def ensure_prepared(cfg: dict, lots: list[str]) -> None:
    man, prep, raw = resolve(cfg, "manifests"), resolve(cfg, "data_prepared"), resolve(cfg, "data_raw")
    for lot in lots:
        pf = prepared_paths(man / "lots" / f"{lot}.csv", prep / "ukdale", cfg["windows"]["ukdale_s"])
        if not all(Path(f).exists() for f in pf):
            print("preparing", lot, prepare_ukdale_lot(man / "lots" / f"{lot}.csv", raw / "ukdale" / cfg["ukdale"]["calibration_file"], prep / "ukdale", cfg))


def pilot_specs(cfg: dict, lot: str) -> list[Spec]:
    reps, sc = cfg["run"]["repetitions_pilot"], cfg["spark"]
    sp = split_of(cfg, lot)
    out = []
    for r in range(1, reps + 1):
        out.append(Spec("B0", "ukdale", "local", lot, "A", "raw", "local", repetition=r, split=sp))
        out.append(Spec("B0", "ukdale", "local", lot, "A", "prepared", "local", repetition=r, split=sp))
        for p in sc["p_values"]:
            for stop in ("decode", "compute", "write"):
                for scope in ("raw", "prepared"):
                    if scope == "prepared" and stop == "decode":
                        continue
                    out.append(Spec("PILOT", "ukdale", "spark", lot, "A", scope, "pilot", p, sc["P_values"][1], sc["Q_default"],
                                    1, "hash", stop, r, split=sp))
        # MetroPT-3: modest workload, startup counted in submit_duration_s
        out.append(Spec("B0", "metropt", "local", "metropt3", "A", "prepared", "local", repetition=r))
        out.append(Spec("B0", "metropt", "local", "metropt3", "A", "raw", "local", repetition=r))
        for p in sc["p_values"]:
            out.append(Spec("PILOT", "metropt", "spark", "metropt3", "A", "prepared", "pilot", p, sc["P_values"][1], 1, 1, repetition=r))
            out.append(Spec("PILOT", "metropt", "spark", "metropt3", "A", "raw", "pilot", p, sc["P_values"][1], 1, 1, repetition=r))
    return out


def grid_specs(cfg: dict, lot: str, Q: int | None = None) -> list[Spec]:
    """Q2: full p x P sweep at ONE volume (AQE on), AQE-off sweep to isolate P, strategy and Q experiments."""
    sc, reps = cfg["spark"], cfg["run"]["repetitions_grid"]
    Q = Q or sc["Q_default"]
    sp = split_of(cfg, lot)
    out = []
    for r in range(1, reps + 1):
        out.append(Spec("B0", "ukdale", "local", lot, "A", "raw", "local", repetition=r, split=sp))
        for p in sc["p_values"]:
            for P in sc["P_values"]:
                out.append(Spec("GRID", "ukdale", "spark", lot, "A", "raw", "grid", p, P, Q, 1, "hash", "write", r, split=sp))
                out.append(Spec("GRID", "ukdale", "spark", lot, "A", "prepared", "grid", p, P, Q, 1, "hash", "write", r, split=sp))
                out.append(Spec("GRID_AQEOFF", "ukdale", "spark", lot, "A", "prepared", "grid-aqe-off", p, P, Q, 0, "hash", "write", r, split=sp))
                out.append(Spec("GRID_STRAT", "ukdale", "spark", lot, "A", "prepared", "grid-range", p, P, Q, 1, "range", "write", r, split=sp))
        pmax = max(sc["p_values"])
        for q in sorted({1, pmax, 4 * pmax, 16 * pmax}):       # read partitions, P fixed
            out.append(Spec("GRID_Q", "ukdale", "spark", lot, "A", "raw", f"grid-Q{q}", pmax, sc["P_values"][1], q, 1, "hash", "write", r, split=sp))
        # Treatment B (required at least on UK-DALE)
        out.append(Spec("B0", "ukdale", "local", lot, "B", "prepared", "local", repetition=r, split=sp))
        for p in sc["p_values"]:
            out.append(Spec("GRID", "ukdale", "spark", lot, "B", "prepared", "grid", p, sc["P_values"][1], Q, 1, "hash", "write", r, split=sp))
    return out


def sizeup_specs(cfg: dict, split: str, P: int, Q: int | None = None, reps: int | None = None) -> list[Spec]:
    """Q1 and size-up: every lot of a split, B0, B1 (Spark p=1) and Spark at each p, fixed P."""
    sc = cfg["spark"]
    Q = Q or sc["Q_default"]
    reps = reps or cfg["run"]["repetitions_grid"]
    out = []
    for lot in lots_of(cfg, split):
        for r in range(1, reps + 1):
            out.append(Spec("B0", "ukdale", "local", lot, "A", "raw", "local", repetition=r, split=split))
            for p in sc["p_values"]:
                out.append(Spec("B1" if p == 1 else "SIZEUP", "ukdale", "spark", lot, "A", "raw", "single-node" if p == 1 else "sizeup",
                                p, P, Q, 1, "hash", "write", r, split=split))
    return out


def final_specs(cfg: dict, decisions: dict) -> list[Spec]:
    """Evaluation on held-out lots: B0, B1 and the frozen/selected configs of B2, B3, B4, B4_nomargin."""
    reps, sc = cfg["run"]["repetitions_final"], cfg["spark"]
    Q = sc["Q_default"]
    out = []
    for lot in lots_of(cfg, "test"):
        for r in range(1, reps + 1):
            out.append(Spec("B0", "ukdale", "local", lot, "A", "raw", "local", repetition=r, split="test"))
            out.append(Spec("B1", "ukdale", "spark", lot, "A", "raw", "single-node", 1, decisions["B2"]["P"], Q, 1, "hash", "write", r, split="test"))
    for d in decisions["decisions"]:
        if not d["feasible"]:
            continue
        for r in range(1, reps + 1):
            out.append(Spec(d["method"], "ukdale", "spark", d["lot"], "A", "raw", f"{d['scenario']}", d["p"], d["P"], Q, 1, "hash",
                            "write", r, deadline_s=d["deadline_s"], split="test"))
    return out


def execute(specs: list[Spec], cfg: dict, budget_only: bool = False) -> None:
    rng = random.Random(cfg["run"]["seed"])
    first = [s for s in specs if s.engine == "local" and s.repetition == 1]
    rest = [s for s in specs if s not in first]
    rng.shuffle(rest)
    ordered = first + rest
    done = completed_ids(resolve(cfg, "results") / "runs.csv")
    todo = [s for s in ordered if s.run_id() not in done]
    print(f"{len(ordered)} runs planned, {len(todo)} to do, per-run timeout {cfg['run']['timeout_s']} s "
          f"(worst case {len(todo) * cfg['run']['timeout_s'] / 3600:.1f} h)")
    runs = resolve(cfg, "results") / "runs.csv"
    if runs.exists():
        df = pd.read_csv(runs)
        med = df[df.status == "OK"].submit_duration_s.median()
        if pd.notna(med):
            print(f"estimated from logged runs: ~{len(todo) * med / 3600:.1f} h (median submit {med:.1f} s)")
    if budget_only:
        return
    for i, s in enumerate(todo, 1):
        r = run_experiment(s, cfg)
        print(f"[{i}/{len(todo)}] {s.method} {s.lot} {s.engine} p={s.p} P={s.P} Q={s.Q} {s.scope} {s.stop_after} r{s.repetition} -> {r['status']} {r['output_check']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["pilot", "grid", "sizeup-cal", "sizeup-test", "final"])
    ap.add_argument("--lot", help="lot for pilot/grid (pilot: smallest calibration lot; grid: a mid calibration lot)")
    ap.add_argument("--P", type=int, help="fixed P for size-up (choose from the grid results)")
    ap.add_argument("--budget-only", action="store_true")
    a = ap.parse_args()
    cfg = load_config()
    cal = lots_of(cfg, "calibration")
    if a.what == "pilot":
        lot = a.lot or cal[0]; ensure_prepared(cfg, [lot]); specs = pilot_specs(cfg, lot)
    elif a.what == "grid":
        lot = a.lot or cal[len(cal) // 2]; ensure_prepared(cfg, [lot]); specs = grid_specs(cfg, lot)
    elif a.what.startswith("sizeup"):
        sp = "calibration" if a.what.endswith("cal") else "test"
        ensure_prepared(cfg, lots_of(cfg, sp)); specs = sizeup_specs(cfg, sp, a.P or cfg["spark"]["P_values"][1])
    else:
        dec = json.loads((resolve(cfg, "results") / "decisions.json").read_text())
        ensure_prepared(cfg, lots_of(cfg, "test")); specs = final_specs(cfg, dec)
    execute(specs, cfg, a.budget_only)
