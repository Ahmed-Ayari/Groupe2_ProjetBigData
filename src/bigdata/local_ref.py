"""B0: local Python reference (chunked pandas/NumPy). Same outputs as the Spark jobs."""
from __future__ import annotations
import time
from pathlib import Path
import numpy as np
import pandas as pd

from . import windows as W
from .ukdale import Calibration, file_partials

METRO_SKIP = {"Unnamed: 0"}


def iter_chunks(path: str | Path, cols: list[str], rows: int):
    """Yield DataFrames of at most `rows` rows from a CSV or Parquet file (bounded memory)."""
    if str(path).endswith(".parquet"):
        import pyarrow.parquet as pq
        for b in pq.ParquetFile(path).iter_batches(batch_size=rows, columns=cols):
            yield b.to_pandas()
    else:
        yield from pd.read_csv(path, chunksize=rows, usecols=cols)


def metropt_columns(csv_path: str | Path, ts_col: str) -> list[str]:
    if str(csv_path).endswith(".parquet"):
        import pyarrow.parquet as pq
        head = pq.ParquetFile(csv_path).schema_arrow.empty_table().to_pandas()
        head = head.drop(columns=[c for c in ("ts_us", "equipment_id") if c in head.columns])
        return [c for c in head.columns if c != ts_col and c not in METRO_SKIP and pd.api.types.is_numeric_dtype(head[c])]
    head = pd.read_csv(csv_path, nrows=5)
    return [c for c in head.columns if c != ts_col and c not in METRO_SKIP and pd.api.types.is_numeric_dtype(head[c])]


def metropt_treatment_a(csv_path: str | Path, cfg: dict) -> pd.DataFrame:
    """Chunked 5-minute windows: n, mean, max, std_pop per sensor. Windows cut by chunks are merged exactly."""
    ts_col, w = cfg["metropt"]["timestamp_col"], cfg["windows"]["metropt_s"]
    cols = metropt_columns(csv_path, ts_col)
    parts = []
    for chunk in iter_chunks(csv_path, [ts_col, *cols], cfg["metropt"]["chunk_rows"]):
        parts.append(W.block_partials(chunk, W.to_ns(chunk[ts_col]), w, cols))
    merged = W.merge_partials(pd.concat(parts, ignore_index=True), cols)
    return W.finalize_generic(merged, cols, w, cfg["metropt"]["equipment_id"])


def metropt_treatment_b(a: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    feats = [c for c in a.columns if c.endswith("__mean")]
    return W.treatment_b(a, feats, cfg["windows"]["metropt_s"], cfg["windows"]["history_s"],
                         {f: f.replace("__mean", "__n") for f in feats})


def ukdale_treatment_a(files: list[str | Path], cal: Calibration, cfg: dict) -> pd.DataFrame:
    """Sequential per-file decode by blocks, then exact merge of partial sums."""
    w = cfg["windows"]["ukdale_s"]
    u = cfg["ukdale"]
    parts = [file_partials(f, cal, w, u["block_seconds"], tuple(u["channel_order"]), u["int_shift_bits"]) for f in files]
    m = W.uk_merge(pd.concat(parts, ignore_index=True))
    return W.uk_finalize(m, w, u["house"])


def ukdale_treatment_b(a: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    return W.treatment_b(a, ["i_rms", "p_mean"], cfg["windows"]["ukdale_s"], cfg["windows"]["history_s"], "n")


def read_lot(lot_csv: str | Path) -> list[str]:
    df = pd.read_csv(lot_csv)
    return df["local_path"].tolist()


def timed(fn, *a, **kw):
    t0 = time.perf_counter()
    r = fn(*a, **kw)
    return r, time.perf_counter() - t0
