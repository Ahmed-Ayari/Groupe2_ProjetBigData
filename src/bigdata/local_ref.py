"""B0: local Python reference (chunked pandas/NumPy). Same outputs as the Spark jobs."""
from __future__ import annotations
import concurrent.futures as cf
import multiprocessing as mp
import os
import time
from pathlib import Path
import numpy as np
import pandas as pd

from . import windows as W
from .ukdale import Calibration, file_partials

METRO_SKIP = {"Unnamed: 0"}
_BLAS_LIMITER = None


def _limit_worker_blas_threads() -> None:
    global _BLAS_LIMITER
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    from threadpoolctl import threadpool_limits
    _BLAS_LIMITER = threadpool_limits(limits=1)


def _file_partials_task(args) -> pd.DataFrame:
    path, cal, w_s, block_seconds, channel_order, int_shift_bits = args
    return file_partials(path, cal, w_s, block_seconds, channel_order, int_shift_bits)


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


def ukdale_treatment_a_mp(files: list[str | Path], cal: Calibration, cfg: dict, workers: int) -> pd.DataFrame:
    """Decode files concurrently, then use the same exact merge as the sequential B0."""
    if workers < 1:
        raise ValueError("workers must be at least 1")
    w, u = cfg["windows"]["ukdale_s"], cfg["ukdale"]
    tasks = [(f, cal, w, u["block_seconds"], tuple(u["channel_order"]), u["int_shift_bits"]) for f in files]
    with cf.ProcessPoolExecutor(max_workers=workers, initializer=_limit_worker_blas_threads,
                                mp_context=mp.get_context("spawn")) as pool:
        parts = list(pool.map(_file_partials_task, tasks))
    if not parts:
        return W.uk_finalize(W.uk_merge(pd.DataFrame(columns=["window_id", *W.UK_SUMS, "max_i"])), w, u["house"])
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
