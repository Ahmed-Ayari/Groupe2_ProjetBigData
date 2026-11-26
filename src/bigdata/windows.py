"""Window arithmetic and exact merging of partial statistics.

Conventions (shared by B0 and Spark):
* window_id = floor(t_ns / (w_s * 1e9)); windows are half-open [id*w, (id+1)*w).
* A window cut across blocks/files is represented by PARTIAL statistics that are merged,
  never by averaging averages.
* Population standard deviation (ddof=0) everywhere.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

NS = 1_000_000_000


def window_ids(t_ns: np.ndarray, w_s: float) -> np.ndarray:
    """Half-open window index for integer nanosecond timestamps."""
    return np.floor_divide(t_ns.astype(np.int64), np.int64(round(w_s * NS)))


def to_ns(ts: pd.Series) -> np.ndarray:
    """Datetime series -> int64 ns since epoch, independent of pandas time unit."""
    s = pd.to_datetime(ts)
    return ((s - pd.Timestamp("1970-01-01")) // pd.Timedelta(1, "ns")).to_numpy(dtype=np.int64)


# ---------------------------------------------------------------- generic (MetroPT) -----------
def block_partials(df: pd.DataFrame, t_ns: np.ndarray, w_s: float, cols: list[str]) -> pd.DataFrame:
    """Per-window (n, mean, M2, max) for each column. M2 = sum (x-mean)^2 (population variance * n)."""
    d = df[cols].copy()
    d["window_id"] = window_ids(t_ns, w_s)
    g = d.groupby("window_id", sort=True)
    out = pd.DataFrame(index=g.size().index)
    for c in cols:
        n = g[c].count()
        mean = g[c].mean()
        centered = d[c] - d["window_id"].map(mean)
        m2 = centered.pow(2).groupby(d["window_id"], sort=True).sum()
        out[f"{c}__n"] = n
        out[f"{c}__mean"] = mean
        out[f"{c}__m2"] = m2
        out[f"{c}__max"] = g[c].max()
    return out.reset_index()


def merge_partials(parts: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Exact merge (Chan et al.): N=sum n; mean=sum(n*mean)/N; M2=sum(M2_j + n_j (mean_j-mean)^2)."""
    parts = parts.sort_values("window_id")
    res = pd.DataFrame({"window_id": np.sort(parts["window_id"].unique())}).set_index("window_id")
    for c in cols:
        n = parts[f"{c}__n"].astype(float)
        mean = parts[f"{c}__mean"].fillna(0.0)
        wid = parts["window_id"]
        N = n.groupby(wid).sum()
        gmean = (n * mean).groupby(wid).sum() / N.where(N > 0)
        dev = n * (mean - wid.map(gmean).fillna(0.0)) ** 2
        M2 = (parts[f"{c}__m2"].fillna(0.0) + dev).groupby(wid).sum()
        res[f"{c}__n"] = N
        res[f"{c}__mean"] = gmean
        res[f"{c}__max"] = parts.groupby("window_id")[f"{c}__max"].max()
        res[f"{c}__std_pop"] = np.sqrt(M2 / N.where(N > 0))
    return res.reset_index()


def finalize_generic(merged: pd.DataFrame, cols: list[str], w_s: float, equipment_id: str) -> pd.DataFrame:
    out = pd.DataFrame({"equipment_id": equipment_id, "window_id": merged["window_id"].astype("int64")})
    out["window_start_s"] = out["window_id"] * w_s
    for c in cols:
        out[f"{c}__n"] = merged[f"{c}__n"].astype("int64")
        out[f"{c}__mean"] = merged[f"{c}__mean"]
        out[f"{c}__max"] = merged[f"{c}__max"]
        out[f"{c}__std_pop"] = merged[f"{c}__std_pop"]
    return out


# ---------------------------------------------------------------- UK-DALE ----------------------
UK_SUMS = ["n", "sum_i2", "sum_u2", "sum_p"]


def uk_block_partials(u: np.ndarray, i: np.ndarray, t_ns: np.ndarray, w_s: float) -> pd.DataFrame:
    """Compact partial sums per window for calibrated voltage u [V] and current i [A]."""
    wid = window_ids(t_ns, w_s)
    df = pd.DataFrame({"window_id": wid, "i2": i * i, "u2": u * u, "p": u * i, "ia": np.abs(i)})
    g = df.groupby("window_id", sort=True)
    return pd.DataFrame({
        "n": g.size().astype("int64"),
        "sum_i2": g["i2"].sum(), "sum_u2": g["u2"].sum(), "sum_p": g["p"].sum(),
        "max_i": g["ia"].max(),
    }).reset_index()


def uk_merge(parts: pd.DataFrame) -> pd.DataFrame:
    g = parts.groupby("window_id", sort=True)
    return pd.DataFrame({
        "n": g["n"].sum().astype("int64"),
        "sum_i2": g["sum_i2"].sum(), "sum_u2": g["sum_u2"].sum(), "sum_p": g["sum_p"].sum(),
        "max_i": g["max_i"].max(),
    }).reset_index()


def uk_finalize(m: pd.DataFrame, w_s: float, equipment_id: str) -> pd.DataFrame:
    return pd.DataFrame({
        "equipment_id": equipment_id,
        "window_id": m["window_id"].astype("int64"),
        "window_start_s": m["window_id"] * w_s,
        "n": m["n"].astype("int64"),
        "i_rms": np.sqrt(m["sum_i2"] / m["n"]),
        "v_rms": np.sqrt(m["sum_u2"] / m["n"]),
        "p_mean": m["sum_p"] / m["n"],
        "i_max": m["max_i"],
    })


# ---------------------------------------------------------------- Treatment B ------------------
def treatment_b(win: pd.DataFrame, feats: list[str], w_s: float, history_s: float, n_col: str | dict) -> pd.DataFrame:
    """Time-based temporal features for each existing window.

    delta_<f>  : f(t) - f(t-1 window), NaN if the previous window is missing (gap) -> prev_missing=1
    hist_<f>   : n-weighted mean of f over windows with ids in [t-k, t-1], k = history_s / w_s,
                 NaN if no window exists in that range. Rows are NOT counted by position.
    """
    k = int(round(history_s / w_s))
    out = win.sort_values(["equipment_id", "window_id"]).reset_index(drop=True).copy()
    res = []
    for eq, g in out.groupby("equipment_id", sort=False):
        g = g.set_index("window_id")
        grid = pd.RangeIndex(g.index.min(), g.index.max() + 1, name="window_id")
        gg = g.reindex(grid)
        r = pd.DataFrame(index=g.index)
        prev_exists = gg.index.to_series().shift(1).isin(g.index) & (gg.index.to_series() > g.index.min())
        r["prev_missing"] = (~prev_exists.reindex(g.index)).astype(int)
        for f in feats:
            ncol = n_col[f] if isinstance(n_col, dict) else n_col
            n = gg[ncol].astype(float).fillna(0.0)
            num = (n * gg[f].fillna(0.0)).rolling(k, min_periods=1).sum().shift(1)
            den = n.rolling(k, min_periods=1).sum().shift(1)
            hist = num / den.where(den > 0)
            prev = gg[f].shift(1)
            r[f"delta_{f}"] = (g[f] - prev.reindex(g.index)).where(prev_exists.reindex(g.index))
            r[f"hist_{f}"] = hist.reindex(g.index)
        r["equipment_id"] = eq
        res.append(r.reset_index())
    b = pd.concat(res, ignore_index=True)
    return out.merge(b, on=["equipment_id", "window_id"], how="left")
