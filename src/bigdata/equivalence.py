"""Output equivalence: Spark/B-method output vs the B0 reference, with frozen tolerances."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

from .config import tol

MAX_ROWS = 5_000_000   # safety: outputs are window tables, small; refuse to load anything huge


def read_parquet_dir(path: str | Path) -> pd.DataFrame:
    import pyarrow.dataset as ds
    d = ds.dataset(str(path), format="parquet")
    if d.count_rows() > MAX_ROWS:
        raise RuntimeError(f"refusing to load {d.count_rows()} rows into the driver-side checker")
    return d.to_table().to_pandas()


def compare(a: pd.DataFrame, b: pd.DataFrame, atol: float, rtol: float,
            keys=("equipment_id", "window_id")) -> dict:
    """a = candidate, b = reference. NaN==NaN accepted; NaN vs number is a failure."""
    res = {"ok": False, "rows_candidate": len(a), "rows_reference": len(b), "atol": atol, "rtol": rtol}
    if set(a.columns) != set(b.columns):
        res["error"] = f"columns differ: {sorted(set(a.columns) ^ set(b.columns))}"
        return res
    a = a.sort_values(list(keys)).reset_index(drop=True)
    b = b.sort_values(list(keys)).reset_index(drop=True)
    if len(a) != len(b):
        res["error"] = "row count differs"
        return res
    for k in keys:
        if not (a[k].to_numpy() == b[k].to_numpy()).all():
            res["error"] = f"key mismatch on {k}"
            return res
    worst, bad = 0.0, []
    for c in b.columns:
        if c in keys or c == "equipment_id":
            continue
        x, y = a[c].to_numpy(dtype=float), b[c].to_numpy(dtype=float)
        ok = np.isclose(x, y, atol=atol, rtol=rtol, equal_nan=True)
        if not ok.all():
            bad.append(c)
        with np.errstate(invalid="ignore"):
            d = np.nanmax(np.abs(x - y) / (atol + rtol * np.abs(y))) if len(x) else 0.0
        worst = max(worst, float(0.0 if np.isnan(d) else d))
    res.update({"ok": not bad, "bad_columns": bad, "max_scaled_error": worst})
    return res


def check_run(out_path: str | Path, ref_path: str | Path, cfg: dict, kind: str, run_id: str, results_dir: Path) -> dict:
    atol, rtol = tol(cfg, "ukdale" if kind == "ukdale" else "default")
    r = compare(read_parquet_dir(out_path), read_parquet_dir(ref_path), atol, rtol)
    r["run_id"] = run_id
    d = results_dir / "equivalence"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{run_id}.json").write_text(json.dumps(r, indent=2))
    return r
