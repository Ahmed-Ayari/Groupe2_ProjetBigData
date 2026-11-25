"""Selector logic on a SYNTHETIC runs table (a made-up law, only to test the code paths) and split hygiene."""
import json
import numpy as np
import pandas as pd
import pytest
from bigdata import campaign as C, selector as S, lots as L
from bigdata.config import ROOT, load_config
from bigdata.runner import ALL


def fake_env(tmp_path, cfg):
    cfg = json.loads(json.dumps(cfg))
    cfg["paths"]["results"] = str(tmp_path / "res")
    cfg["paths"]["manifests"] = str(tmp_path / "man")
    cfg["spark"]["p_values"], cfg["spark"]["P_values"] = [1, 2, 4], [16, 64]
    (tmp_path / "res").mkdir(); (tmp_path / "man" / "lots").mkdir(parents=True)
    rng = np.random.default_rng(0)
    sizes = {"cal_1": 0.5, "test_1": 0.75, "cal_2": 1.0, "test_2": 1.5, "cal_3": 2.0, "test_3": 3.0}
    splits, rows = {}, []
    for lot, gb in sizes.items():
        n = int(gb * 40)
        pd.DataFrame({"local_path": [f"{lot}_{i}" for i in range(n)], "source_bytes": [int(gb * 2**30 / n)] * n}).to_csv(tmp_path / "man" / "lots" / f"{lot}.csv", index=False)
        sp = "test" if lot.startswith("test") else "calibration"
        splits[lot] = {"split": sp, "files": n, "source_gb": gb}
        if sp == "calibration":
            for p in (1, 2, 4):
                for P in (16, 64):
                    for r in range(3):
                        T = 20 * gb / (p ** 0.8) * (1 + 0.1 * (P == 16)) * rng.lognormal(0, 0.05)
                        rows.append({c: "" for c in ALL} | {"run_id": f"{lot}{p}{P}{r}", "lot_id": lot, "dataset": "ukdale", "workload": "A", "scope": "raw",
                                      "engine": "spark", "stop_after": "write", "status": "OK", "output_check": "ok", "split": "calibration", "AQE": 1,
                                      "strategy": "hash", "method": "GRID", "p": p, "P_initial": P, "duration_s": T, "submit_duration_s": T + 8})
    (tmp_path / "man" / "splits.json").write_text(json.dumps(splits))
    pd.DataFrame(rows).to_csv(tmp_path / "res" / "runs.csv", index=False)
    return cfg


def test_fit_and_decide_and_no_leak(tmp_path, cfg):
    c = fake_env(tmp_path, cfg)
    out = S.fit_and_decide(c)
    assert set(out["calibration_lots"]) == {"cal_1", "cal_2", "cal_3"}          # no test lot in calibration
    assert out["margin_s"] >= 0 and out["model"] in out["cv"]
    d = pd.DataFrame(out["decisions"])
    assert set(d.lot) == {"test_1", "test_2", "test_3"}
    b4 = d[(d.method == "B4") & d.feasible]
    assert (b4.T_hat + out["margin_s"] <= b4.deadline_s + 1e-9).all()           # constraint respected
    nm = d[d.method == "B4_nomargin"]
    assert len(nm) == len(d[d.method == "B4"])


def test_deadlines_defined_from_calibration_only(tmp_path, cfg):
    c = fake_env(tmp_path, cfg)
    runs = pd.read_csv(tmp_path / "res" / "runs.csv")
    feats = S.lot_features(c)
    cal = S.calibration_table(runs, feats, c)
    assert (cal.lot_id.str.startswith("cal")).all()


def test_choose_returns_explicit_infeasible(tmp_path, cfg):
    c = fake_env(tmp_path, cfg)
    cal = S.calibration_table(pd.read_csv(tmp_path / "res" / "runs.csv"), S.lot_features(c), c)
    m = S.LogLinModel().fit(cal)
    row = S.lot_features(c).set_index("lot_id").loc["test_3"]
    assert S.choose(m, row, D=0.001, margin=0.0, cands=S.candidates(c))["feasible"] is False


def test_final_budget_specs_work_before_fit_and_cover_maximum_decisions(tmp_path, cfg):
    c = json.loads(json.dumps(cfg))
    c["paths"]["manifests"] = str(tmp_path)
    c["run"]["repetitions_final"] = 2
    c["selector"]["deadline_scenarios"] = {"moderate": 0.5, "tight": 0.8}
    (tmp_path / "splits.json").write_text(json.dumps({
        "cal_1": {"split": "calibration", "source_gb": 0.5},
        "test_1": {"split": "test", "source_gb": 0.75},
        "test_2": {"split": "test", "source_gb": 1.5},
    }))

    specs = C.final_budget_specs(c)

    assert len(specs) == 2 * 2 * (2 + 2 * 4)
    assert len({spec.run_id() for spec in specs}) == len(specs)
    assert {spec.method for spec in specs} == {"B0", "B1", "B2", "B3", "B4", "B4_nomargin"}


def test_sizeup_repetitions_are_independent_of_grid_repetitions(tmp_path, cfg):
    c = json.loads(json.dumps(cfg))
    c["paths"]["manifests"] = str(tmp_path)
    c["run"]["repetitions_grid"] = 3
    c["run"]["repetitions_sizeup"] = 2
    (tmp_path / "splits.json").write_text(json.dumps({
        "cal_1": {"split": "calibration", "source_gb": 0.5},
    }))

    specs = C.sizeup_specs(c, "calibration", 64)

    assert {spec.repetition for spec in specs} == {1, 2}


def test_lots_disjoint_and_ratio():
    files = pd.DataFrame({"local_path": [f"f{i}" for i in range(500)], "start": range(500), "source_bytes": [24 * 2**20] * 500})
    lots = L.plan_lots(files, [0.5, 1, 2], [0.75, 1.5, 3])
    L.check_disjoint(lots)
    assert L.ratio_ok(lots, "calibration", 4) and L.ratio_ok(lots, "test", 4)
    lots["cal_1"] = pd.concat([lots["cal_1"], lots["test_1"].iloc[:1].assign(split="calibration")])
    with pytest.raises(AssertionError):
        L.check_disjoint(lots)


def test_lots_expand_largest_to_keep_realized_ratio_with_large_files():
    file_bytes = int(0.2 * 2**30)
    files = pd.DataFrame({
        "local_path": [f"f{i}" for i in range(100)],
        "start": range(100),
        "source_bytes": [file_bytes] * 100,
    })
    lots = L.plan_lots(files, [0.25, 0.5, 1.0], [0.4, 0.8, 1.6])
    assert L.ratio_ok(lots, "calibration", 4)
    assert L.ratio_ok(lots, "test", 4)
    assert lots["cal_3"].source_bytes.sum() >= 4 * lots["cal_1"].source_bytes.sum()
    assert lots["test_3"].source_bytes.sum() >= 4 * lots["test_1"].source_bytes.sum()


def test_default_lot_targets_keep_requested_extreme_ratio():
    default = load_config(ROOT / "configs" / "default.yaml")
    calibration = default["lots"]["calibration_gb"]
    test = default["lots"]["test_gb"]
    assert calibration == [0.25, 0.5, 1.0]
    assert test == [0.4, 0.8, 1.6]
    assert max(calibration) / min(calibration) >= 4
    assert max(test) / min(test) >= 4


def test_bootstrap_is_deterministic():
    r = np.array([0.8, 0.9, 1.0])
    assert S.paired_bootstrap(r) == S.paired_bootstrap(r)
