"""Preparation steps (their cost is reported separately from the benchmark durations)."""
from __future__ import annotations
import argparse, csv, json, time
from pathlib import Path
import numpy as np
import pandas as pd

from . import windows as W
from .config import load_config, resolve
from .ukdale import parse_calibration, file_partials


def log_cost(cfg: dict, name: str, seconds: float, in_bytes: int, out_bytes: int) -> None:
    f = resolve(cfg, "results") / "preparation_costs.csv"
    f.parent.mkdir(parents=True, exist_ok=True)
    new = not f.exists()
    with open(f, "a", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["step", "seconds", "input_bytes", "output_bytes", "timestamp"])
        w.writerow([name, f"{seconds:.3f}", in_bytes, out_bytes, pd.Timestamp.now("UTC").isoformat()])


def prepare_metropt(csv_path: Path, out_parquet: Path, cfg: dict) -> dict:
    """CSV -> typed Parquet. Global exact-duplicate removal, sort by time, add ts_us (int64 microseconds, UTC-naive)."""
    t0 = time.perf_counter()
    ts_col = cfg["metropt"]["timestamp_col"]
    df = pd.read_csv(csv_path)
    df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")])
    before = len(df)
    df[ts_col] = pd.to_datetime(df[ts_col])
    df = df.drop_duplicates().sort_values(ts_col).reset_index(drop=True)
    df["ts_us"] = ((df[ts_col] - pd.Timestamp("1970-01-01")) // pd.Timedelta(1, "us")).astype("int64")
    df["equipment_id"] = cfg["metropt"]["equipment_id"]
    out_parquet.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_parquet, index=False)
    sec = time.perf_counter() - t0
    log_cost(cfg, "metropt_csv_to_parquet", sec, csv_path.stat().st_size, out_parquet.stat().st_size)
    return {"rows_in": before, "rows_out": len(df), "duplicates_removed": before - len(df), "seconds": sec}


def prepare_ukdale_lot(lot_csv: Path, cal_path: Path, out_dir: Path, cfg: dict) -> dict:
    """Decode each FLAC once and keep compact per-(file,window) partial sums in Parquet."""
    t0 = time.perf_counter()
    cal = parse_calibration(cal_path)
    u = cfg["ukdale"]
    lot = pd.read_csv(lot_csv)
    out_dir.mkdir(parents=True, exist_ok=True)
    in_b = out_b = 0
    for lp in lot["local_path"]:
        p = Path(lp)
        part = file_partials(p, cal, cfg["windows"]["ukdale_s"], u["block_seconds"], tuple(u["channel_order"]), u["int_shift_bits"])
        o = out_dir / (p.stem + f"_w{cfg['windows']['ukdale_s']}.parquet")
        part.to_parquet(o, index=False)
        in_b += p.stat().st_size
        out_b += o.stat().st_size
    sec = time.perf_counter() - t0
    log_cost(cfg, f"ukdale_prepare_{lot_csv.stem}", sec, in_b, out_b)
    return {"files": len(lot), "seconds": sec, "input_bytes": in_b, "output_bytes": out_b}


def prepared_paths(lot_csv: Path, out_dir: Path, w_s) -> list[str]:
    lot = pd.read_csv(lot_csv)
    return [str(out_dir / (Path(p).stem + f"_w{w_s}.parquet")) for p in lot["local_path"]]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["metropt", "ukdale"])
    ap.add_argument("--lot")
    a = ap.parse_args()
    cfg = load_config()
    raw, prep, man = resolve(cfg, "data_raw"), resolve(cfg, "data_prepared"), resolve(cfg, "manifests")
    if a.what == "metropt":
        m = json.loads((man / "metropt3.json").read_text())
        print(prepare_metropt(Path(m["csv_path"]), Path(m["parquet_path"]), cfg))
    else:
        print(prepare_ukdale_lot(man / "lots" / f"{a.lot}.csv", raw / "ukdale" / cfg["ukdale"]["calibration_file"], prep / "ukdale", cfg))
