"""Selector logic on a SYNTHETIC runs table (a made-up law, only to test the code paths) and split hygiene."""
import json
import numpy as np
import pandas as pd
import pytest
from bigdata import campaign as C, selector as S, lots as L
from bigdata.config import ROOT, load_config
from bigdata import runner as R
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


def test_fit_and_decide_and_no_leak(tmp_path, cfg, capsys):
    c = fake_env(tmp_path, cfg)
    c["selector"]["deadline_scenarios"] = {"moderate": 0.5, "tight": 0.8, "strict": 0.2}
    out = S.fit_and_decide(c)
    printed = capsys.readouterr().out
    assert all(f"{scenario}: calibration (p,P,lot) configs meeting deadline =" in printed
               for scenario in ("moderate", "tight", "strict"))
    assert set(out["calibration_lots"]) == {"cal_1", "cal_2", "cal_3"}          # no test lot in calibration
    assert out["margin_relative"] >= 0 and out["model"] in out["cv"]
    d = pd.DataFrame(out["decisions"])
    assert set(d.lot) == {"test_1", "test_2", "test_3"}
    b4 = d[(d.method == "B4") & d.feasible]
    assert (b4.T_hat * (1 + out["margin_relative"]) <= b4.deadline_s + 1e-9).all()
    assert (b4.margin == out["margin_relative"]).all()
    nm = d[d.method == "B4_nomargin"]
    assert len(nm) == len(d[d.method == "B4"])
    assert (nm.margin == 0).all()


def test_relative_margin_is_multiplicative():
    class Fixed:
        def predict(self, d):
            return np.full(len(d), 10.0)

    row = pd.Series({"V": 1.0, "n_files": 1, "mean_file": 1.0, "std_file": 0.0})
    cands = pd.DataFrame({"p": [1], "P": [16]})
    assert not S.choose(Fixed(), row, D=10.5, margin=0.1, cands=cands)["feasible"]


def test_evaluate_counts_infeasible_repetitions_as_deadline_misses(tmp_path, cfg):
    c = json.loads(json.dumps(cfg))
    c["paths"]["results"] = str(tmp_path / "res")
    results = tmp_path / "res"
    results.mkdir()
    pd.DataFrame(columns=ALL).to_csv(results / "runs.csv", index=False)
    (results / "decisions.json").write_text(json.dumps({"decisions": [{
        "lot": "test_1", "scenario": "strict", "method": "B4", "deadline_s": 1.0, "feasible": False,
    }]}))
    summary = S.evaluate(c)
    row = pd.read_csv(results / "final_by_lot.csv").iloc[0]
    assert row.n == c["run"]["repetitions_final"]
    assert row.hits == 0
    assert summary.iloc[0].hit_rate == 0
    assert summary.iloc[0].infeasible_decisions == 1
    paired = pd.read_csv(results / "final_paired.csv")
    aggregate = paired[paired.lot == "ALL"].iloc[0]
    assert pd.isna(aggregate.ci_low) and "fewer than 5" in aggregate.ci_method
    assert "Fewer than 5 independent test lots" in aggregate.note


def test_evaluate_reports_paired_repetition_ratios_and_dispersion(tmp_path, cfg):
    c = json.loads(json.dumps(cfg))
    c["paths"]["results"] = str(tmp_path / "res")
    c["run"]["repetitions_final"] = 5
    results = tmp_path / "res"
    results.mkdir()
    rows = []
    baseline = [10.0, 11.0, 9.0, 10.5, 9.5]
    for method, scale in (("B3", 1.0), ("B4", 1.01)):
        for repetition, duration in enumerate(baseline, 1):
            rows.append({**{column: "" for column in ALL}, "method": method, "dataset": "ukdale",
                         "workload": "A", "scope": "raw", "engine": "spark", "split": "test",
                         "lot_id": "test_1", "policy": "strict", "status": "OK", "p": 2, "P_initial": 16,
                         "duration_s": duration * scale, "repetition": repetition})
    pd.DataFrame(rows, columns=ALL).to_csv(results / "runs.csv", index=False)
    decisions = [{"lot": "test_1", "scenario": "strict", "method": method, "deadline_s": 100.0,
                  "feasible": True, "p": 2, "P": 16, "T_hat": 10.0}
                 for method in ("B3", "B4")]
    (results / "decisions.json").write_text(json.dumps({"decisions": decisions}))
    S.evaluate(c)
    paired = pd.read_csv(results / "final_paired.csv")
    lot = paired[paired.lot == "test_1"].iloc[0]
    assert lot.ratio_min == pytest.approx(1.01)
    assert lot.ratio_max == pytest.approx(1.01)
    assert lot.interpretation == "no measurable difference"
    assert "Fewer than 5 independent test lots" in paired[paired.lot == "ALL"].iloc[0].note


def test_deadlines_defined_from_calibration_only(tmp_path, cfg):
    c = fake_env(tmp_path, cfg)
    runs = pd.read_csv(tmp_path / "res" / "runs.csv")
    feats = S.lot_features(c)
    cal = S.calibration_table(runs, feats, c)
    assert (cal.lot_id.str.startswith("cal")).all()


@pytest.mark.parametrize(("q", "expected"), [(0.85, 0.85), (0.15, 0.15)])
def test_deadlines_accept_hit_fraction_boundaries(cfg, q, expected, capsys):
    cal = pd.DataFrame([
        {"p": 1, "P": 16, "lot_id": f"lot{i}", "T": 1 / i, "V": 1.0}
        for i in range(1, 21)
    ])
    feats = pd.DataFrame({"lot_id": ["unused"], "V": [1.0]})
    c = json.loads(json.dumps(cfg))
    c["selector"]["deadline_scenarios"] = {"boundary": q}

    S.deadlines(cal, feats, c, [])

    assert f"boundary: calibration (p,P,lot) configs meeting deadline = {expected:.1%}" in capsys.readouterr().out


def test_deadlines_error_reports_fraction_and_scenario(cfg):
    cal = pd.DataFrame([
        {"p": 1, "P": 16, "lot_id": f"lot{i}", "T": 1 / i, "V": 1.0}
        for i in range(1, 21)
    ])
    feats = pd.DataFrame({"lot_id": ["unused"], "V": [1.0]})
    c = json.loads(json.dumps(cfg))
    c["selector"]["deadline_scenarios"] = {"too_loose": 0.9}

    with pytest.raises(RuntimeError, match=r"90\.0%.*too_loose"):
        S.deadlines(cal, feats, c, [])


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

    assert len(specs) == 2 * 2 * (2 + 1 + 2 * 4)
    assert len({spec.run_id() for spec in specs}) == len(specs)
    assert {spec.method for spec in specs} == {"B0", "B0mp", "B1", "B2", "B3", "B4", "B4_nomargin"}
    assert {spec.p for spec in specs if spec.method == "B0mp"} == {2}


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


def test_second_calibration_grid_and_b0mp_workers_are_in_campaigns(tmp_path, cfg):
    c = json.loads(json.dumps(cfg))
    c["paths"]["manifests"] = str(tmp_path)
    c["spark"]["p_values"] = [1, 2, 4]
    c["run"]["repetitions_grid"] = 3
    (tmp_path / "splits.json").write_text(json.dumps({
        "cal_1": {"split": "calibration", "source_gb": 0.5},
        "cal_2": {"split": "calibration", "source_gb": 1.0},
        "test_1": {"split": "test", "source_gb": 0.75},
    }))
    grid = C.grid_specs(c, ["cal_2", "cal_1"])
    sweep = [s for s in grid if s.method == "GRID" and s.workload == "A" and s.scope == "raw"]
    assert {s.lot for s in sweep} == {"cal_1", "cal_2"}
    assert all(len([s for s in sweep if s.lot == lot and s.p == p and s.P == P]) == 3
               for lot in ("cal_1", "cal_2") for p in (1, 2, 4) for P in c["spark"]["P_values"])
    sizeup = C.sizeup_specs(c, "calibration", 64)
    assert {s.p for s in sizeup if s.method == "B0mp"} == {2, 4}
    final = C.final_specs(c, {"B2": {"P": 64}, "decisions": []})
    assert {s.p for s in final if s.method == "B0mp"} == {2, 4}


def test_run_ids_change_with_code_version(monkeypatch, cfg):
    spec = R.Spec("B0", "ukdale", "local", "cal_1")
    monkeypatch.setattr(R, "git_hash", lambda: "version-a")
    first = spec.run_id()
    monkeypatch.setattr(R, "git_hash", lambda: "version-b")
    assert first != spec.run_id()


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
