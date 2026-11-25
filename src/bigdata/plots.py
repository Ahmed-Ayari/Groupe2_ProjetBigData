"""All figures are generated from results/runs.csv (and selector outputs) by this script. No hand-typed numbers.

Each figure gets <name>.png and <name>.md (what it shows / does NOT show / hypothesis tested / number of trials).
Figures whose data are not available are skipped and listed in figures_skipped.txt (nothing is fabricated).
"""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import load_config, resolve

SKIPPED: list[str] = []


def _save(fig, out: Path, name: str, shows: str, not_shows: str, hyp: str, n: str) -> None:
    fig.tight_layout()
    fig.savefig(out / f"{name}.png", dpi=150)
    plt.close(fig)
    (out / f"{name}.md").write_text(f"# {name}\n\n- Shows: {shows}\n- Does NOT show: {not_shows}\n- Hypothesis tested: {hyp}\n"
                                    f"- Trials: {n}\n- Script: src/bigdata/plots.py (data: results/runs.csv)\n")


def _ok(runs: pd.DataFrame) -> pd.DataFrame:
    r = runs[(runs.status == "OK") & (runs.stop_after == "write")].copy()
    r["GB"] = pd.to_numeric(r.source_bytes, errors="coerce") / 2**30
    r["duration_s"] = pd.to_numeric(r.duration_s, errors="coerce")
    r["p"] = pd.to_numeric(r.p, errors="coerce")
    r["P_initial"] = pd.to_numeric(r.P_initial, errors="coerce")
    return r


def fig_time_vs_volume(runs, out):
    r = _ok(runs); r = r[(r.dataset == "ukdale") & (r.workload == "A") & (r.scope == "raw")]
    r["label"] = np.where(r.engine == "local", "B0 local Python", "Spark p=" + r.p.astype("Int64").astype(str))
    r = r[r.method.isin(["B0", "B1", "SIZEUP"])]
    if r.empty: return SKIPPED.append("time_vs_volume")
    fig, ax = plt.subplots(figsize=(6, 4))
    for lab, g in r.groupby("label"):
        s = g.groupby("GB").duration_s.agg(["median", "min", "max"]).reset_index()
        ax.errorbar(s.GB, s["median"], yerr=[s["median"] - s["min"], s["max"] - s["median"]], marker="o", capsize=3, label=lab)
    ax.set(xlabel="Source volume (GB of FLAC)", ylabel="Duration, raw scope (s)", title="Duration vs volume, UK-DALE treatment A", xscale="log", yscale="log")
    ax.legend(); n = f"{len(r)} runs (median with min-max bars)"
    _save(fig, out, "fig_time_vs_volume", "median duration per method and lot size; crossover if the curves cross",
          "behaviour beyond the largest lot, or on another machine/cluster", "Q1 / H1", n)


def fig_speedup(runs, out):
    r = _ok(runs); r = r[(r.dataset == "ukdale") & (r.method == "GRID") & (r.scope == "raw") & (r.workload == "A")]
    if r.empty: return SKIPPED.append("speedup_efficiency")
    P0 = sorted(r.P_initial.dropna().unique())[len(r.P_initial.dropna().unique()) // 2]
    g = r[r.P_initial == P0].groupby("p").duration_s.median()
    p0 = g.index.min(); S = g.loc[p0] / g; E = S / (g.index / p0)
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.6))
    ax[0].plot(g.index, S.values, "o-", label="measured"); ax[0].plot(g.index, g.index / p0, "k--", label="ideal")
    ax[0].set(xlabel="p (local[p] cores)", ylabel="Relative speedup S(p)", title=f"Speedup at fixed volume, P={int(P0)}"); ax[0].legend()
    ax[1].plot(g.index, E.values * 100, "o-"); ax[1].set(xlabel="p (local[p] cores)", ylabel="Relative efficiency (%)", title="Efficiency")
    _save(fig, out, "fig_speedup_efficiency", "S(p)=T(p0)/T(p) and E=S/(p/p0) on one lot", "efficiency is not CPU utilisation; no multi-node claim",
          "H1 (non proportional gain)", f"{len(r[r.P_initial == P0])} runs, local parallelism not a cluster")


def fig_partitions(runs, out):
    r = _ok(runs); r = r[(r.dataset == "ukdale") & (r.scope == "prepared") & (r.workload == "A") & r.method.isin(["GRID", "GRID_AQEOFF"])]
    if r.empty: return SKIPPED.append("partitions_effect")
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
    for (m, p), g in r.groupby(["method", "p"]):
        s = g.groupby("P_initial").agg(T=("duration_s", "median"), sh=("shuffle_write_bytes", lambda x: pd.to_numeric(x, errors="coerce").median() / 2**20),
                                      rss=("peak_rss_mb", "median"))
        lab = f"{'AQE off' if m == 'GRID_AQEOFF' else 'AQE on'}, p={int(p)}"
        ax[0].plot(s.index, s["T"], "o-", label=lab); ax[1].plot(s.index, s.sh, "o-"); ax[2].plot(s.index, s.rss, "o-")
    for a, yl in zip(ax, ["Duration (s)", "Shuffle write (MiB)", "Peak RSS incl. JVM (MiB)"]):
        a.set(xlabel="P (initial shuffle partitions)", ylabel=yl, xscale="log")
    ax[0].legend(fontsize=7)
    _save(fig, out, "fig_partitions_effect", "duration, shuffle volume and memory vs P (prepared scope), AQE on/off", "decode cost (prepared scope excludes it)",
          "H2 / Q2", f"{len(r)} runs")


def fig_cost_and_hits(out_dir: Path, res: Path):
    f = res / "final_summary.csv"
    if not f.exists(): return SKIPPED.append("final_cost_hit_rate")
    s = pd.read_csv(f)
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    for sc, g in s.groupby("scenario"):
        ax[0].bar([f"{m}\n{sc}" for m in g.method], g.hit_rate * 100)
        ax[1].bar([f"{m}\n{sc}" for m in g.method], g.median_cost_core_min)
    ax[0].set(ylabel="Deadline hit rate (%)", title="Hit rate (failures, timeouts, infeasible in denominator)")
    ax[1].set(ylabel="Median cost p x T (core-minutes)", title="Cost (resources-minutes, not kWh)")
    for a in ax: a.tick_params(axis="x", labelsize=7)
    _save(fig, out_dir, "fig_final_cost_hit_rate", "B2/B3/B4 on held-out lots", "energy or CO2; guarantees beyond the lots tested", "H3 / Q3", f"{int(s.runs_or_decisions.sum())} runs or decisions")


def fig_task_times(runs, out):
    r = _ok(runs); r = r[(r.engine == "spark") & (r.dataset == "ukdale")]
    r = r.assign(med=pd.to_numeric(r.task_time_median_s, errors="coerce"), mx=pd.to_numeric(r.task_time_max_s, errors="coerce")).dropna(subset=["med", "mx"])
    if r.empty: return SKIPPED.append("task_times")
    fig, ax = plt.subplots(figsize=(6, 4)); ax.scatter(r.med, r.mx, s=12)
    lim = [0, max(r.mx.max(), r.med.max()) * 1.05]; ax.plot(lim, lim, "k--", lw=0.8)
    ax.set(xlabel="Median task duration (s)", ylabel="Max task duration (s)", title="Task duration dispersion (points above the line: slow tasks)")
    _save(fig, out, "fig_task_times", "max vs median task time per run", "the cause of a slow task (check the Spark event log before saying skew)", "H2", f"{len(r)} runs")


def fig_model_accuracy(out, res: Path):
    f = res / "final_by_lot.csv"
    if not f.exists(): return SKIPPED.append("model_accuracy")
    d = pd.read_csv(f).dropna(subset=["T_hat", "median_T"])
    if d.empty: return SKIPPED.append("model_accuracy")
    fig, ax = plt.subplots(figsize=(4.5, 4)); ax.scatter(d.T_hat, d.median_T)
    lim = [0, max(d.T_hat.max(), d.median_T.max()) * 1.05]; ax.plot(lim, lim, "k--")
    ax.set(xlabel="Predicted T (s)", ylabel="Measured median T (s)", title="Duration model on held-out lots")
    mape = float(np.mean(np.abs(d.median_T - d.T_hat) / d.median_T))
    _save(fig, out, "fig_model_accuracy", f"held-out accuracy of the chosen configs (MAPE {mape:.1%})", "accuracy on unseen volumes beyond the lots tested", "Q3", f"{len(d)} lot/scenario points")


def table_failures(runs, res: Path):
    t = runs.groupby(["method", "dataset", "status"]).size().rename("n_runs").reset_index()
    t.to_csv(res / "table_feasibility_failures.csv", index=False)
    e = runs[runs.output_check.isin(["ok", "fail"])].groupby(["method", "output_check"]).size().rename("n").reset_index()
    e.to_csv(res / "table_equivalence.csv", index=False)
    pc = res / "preparation_costs.csv"
    if pc.exists():
        pd.read_csv(pc).to_csv(res / "table_preparation_cost.csv", index=False)


def main() -> None:
    cfg = load_config(); res = resolve(cfg, "results"); out = res / "figures"; out.mkdir(parents=True, exist_ok=True)
    runs = pd.read_csv(res / "runs.csv", low_memory=False)
    for f in (fig_time_vs_volume, fig_speedup, fig_partitions, fig_task_times):
        f(runs, out)
    fig_cost_and_hits(out, res); fig_model_accuracy(out, res); table_failures(runs, res)
    (out / "figures_skipped.txt").write_text("\n".join(SKIPPED))
    print("figures done; skipped:", SKIPPED)


if __name__ == "__main__":
    main()
