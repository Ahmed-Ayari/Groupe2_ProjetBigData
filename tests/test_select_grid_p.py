import runpy
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "select_grid_p.py"
choose_best_p = runpy.run_path(str(SCRIPT))["choose_best_p"]


def test_choose_best_p_uses_median_successful_equivalent_grid_runs():
    rows = []
    for p, duration in ((16, 8.0), (16, 12.0), (64, 7.0), (64, 9.0), (256, 1.0)):
        rows.append({
            "dataset": "ukdale", "method": "GRID", "workload": "A", "scope": "raw", "engine": "spark",
            "stop_after": "write", "status": "OK", "output_check": "ok", "AQE": 1, "strategy": "hash",
            "split": "calibration", "P_initial": p, "duration_s": duration,
        })
    rows[-1]["output_check"] = "fail"
    rows.append(rows[-1] | {"status": "ERROR", "duration_s": 0.1})
    best_p, median_s = choose_best_p(pd.DataFrame(rows))
    assert (best_p, median_s) == (64, 8.0)
