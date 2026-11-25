#!/usr/bin/env python3
"""Choose the P with the lowest median successful raw-scope GRID runtime."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def choose_best_p(runs: pd.DataFrame) -> tuple[int, float]:
    required = {"dataset", "method", "workload", "scope", "engine", "stop_after", "status",
                "output_check", "AQE", "strategy", "split", "P_initial", "duration_s"}
    missing = required - set(runs.columns)
    if missing:
        raise ValueError(f"runs table missing columns: {', '.join(sorted(missing))}")
    rows = runs[
        (runs.dataset == "ukdale") & (runs.method == "GRID") & (runs.workload == "A")
        & (runs.scope == "raw") & (runs.engine == "spark") & (runs.stop_after == "write")
        & (runs.status == "OK") & (runs.output_check == "ok")
        & (pd.to_numeric(runs.AQE, errors="coerce") == 1) & (runs.strategy == "hash")
        & (runs.split == "calibration")
    ].copy()
    rows["P_initial"] = pd.to_numeric(rows.P_initial, errors="coerce")
    rows["duration_s"] = pd.to_numeric(rows.duration_s, errors="coerce")
    rows = rows.dropna(subset=["P_initial", "duration_s"])
    if rows.empty:
        raise ValueError("no successful, equivalence-checked raw-scope GRID runs found")
    medians = rows.groupby("P_initial").duration_s.median()
    best_p = int(sorted(medians.items(), key=lambda item: (item[1], item[0]))[0][0])
    return best_p, float(medians.loc[best_p])


def main() -> int:
    runs_path = ROOT / "results" / "runs.csv"
    if not runs_path.exists():
        print(f"missing grid results: {runs_path}", file=sys.stderr)
        return 2
    try:
        best_p, median_s = choose_best_p(pd.read_csv(runs_path, low_memory=False))
    except (OSError, ValueError) as exc:
        print(f"cannot choose P: {exc}", file=sys.stderr)
        return 2
    print(f"Selected P={best_p} (lowest median GRID duration: {median_s:.3f} s)", file=sys.stderr)
    print(best_p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
