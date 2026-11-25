"""Data mining on MetroPT-3 window indicators: IsolationForest with chronological splits.

Detects an ONGOING abnormal behaviour; it does not demonstrate failure prediction.
Incident intervals come from the configured, source-documented CSV; evaluation stops if it is missing or unverified.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from .config import ROOT, load_config, resolve
from . import local_ref


def features(cfg: dict, source: Path) -> pd.DataFrame:
    a = local_ref.metropt_treatment_a(source, cfg)
    b = local_ref.metropt_treatment_b(a, cfg)
    b["t"] = pd.to_datetime(b["window_start_s"], unit="s")
    return b


def split_masks(df: pd.DataFrame, cfg: dict):
    s = cfg["mining"]["split"]
    tr_end, va_end = pd.Timestamp(s["train_end"]), pd.Timestamp(s["val_end"])
    return df.t < tr_end, (df.t >= tr_end) & (df.t < va_end), df.t >= va_end


def load_incidents(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    inc = pd.read_csv(path)
    if inc.empty or not (inc["verified"].astype(str).str.lower() == "yes").all():
        return None
    inc["start"], inc["end"] = pd.to_datetime(inc["start"]), pd.to_datetime(inc["end"])
    return inc


def episodes(flag: np.ndarray, k: int) -> list[tuple[int, int]]:
    """Alert episodes: runs where `flag` is True on >= k consecutive windows. Returns (first_idx, last_idx)."""
    out, i, n = [], 0, len(flag)
    while i < n:
        if flag[i]:
            j = i
            while j + 1 < n and flag[j + 1]:
                j += 1
            if j - i + 1 >= k:
                out.append((i + k - 1, j))      # alert raised when the k-th consecutive window is reached
            i = j + 1
        else:
            i += 1
    return out


def run(cfg: dict, source: Path) -> dict:
    df = features(cfg, source)
    num = [c for c in df.columns if c.endswith(("__mean", "__max", "__std_pop")) or c.startswith(("delta_", "hist_"))] + ["prev_missing"]
    X = df[num].fillna(0.0)
    tr, va, te = split_masks(df, cfg)
    if min(int(tr.sum()), int(va.sum()), int(te.sum())) == 0:
        raise SystemExit(f"empty split (train/val/test windows = {int(tr.sum())}/{int(va.sum())}/{int(te.sum())}); "
                         f"data covers {df.t.min()} to {df.t.max()}: set mining.split dates in the config from the audit")
    incident_path = Path(cfg["mining"]["incidents"])
    if not incident_path.is_absolute():
        incident_path = ROOT / incident_path
    inc = load_incidents(incident_path)
    # training periods: windows outside documented incidents (unknown status is NOT assumed healthy beyond this)
    normal = pd.Series(True, index=df.index)
    if inc is not None:
        for r in inc.itertuples():
            normal &= ~((df.t >= r.start) & (df.t <= r.end))
    sc = StandardScaler().fit(X[tr & normal])
    iso = IsolationForest(n_estimators=200, contamination=cfg["mining"]["contamination"], random_state=cfg["run"]["seed"]).fit(sc.transform(X[tr & normal]))
    score = -iso.score_samples(sc.transform(X))                    # higher = more abnormal
    df["score"] = score
    k, budget = cfg["mining"]["k_consecutive"], cfg["mining"]["false_alert_budget_per_day"]
    va_norm = va & normal
    days = max((df.t[va].max() - df.t[va].min()).total_seconds() / 86400, 1e-9)
    thr = None
    for q in np.linspace(0.90, 0.9999, 400):                       # lowest threshold meeting the validation false-alert budget
        cand = np.quantile(score[va_norm], q)
        eps = episodes((score[va] > cand) & va_norm[va].to_numpy(), k)
        if len(eps) / days <= budget:
            thr = float(cand); break
    out = {"threshold": thr, "n_features": len(num), "k_consecutive": k, "validation_days": days}
    if inc is None:
        out["evaluation"] = (f"STOPPED: {incident_path} is missing or not verified "
                             "(start,end,label,verified=yes); no incident dates are invented by this code.")
        resolve(cfg, "results").mkdir(parents=True, exist_ok=True)
        df[["equipment_id", "window_id", "t", "score"]].to_parquet(resolve(cfg, "results") / "metropt_scores.parquet", index=False)
        return out
    tt = df[te].reset_index(drop=True)
    flag = (tt.score > thr).to_numpy()
    eps = episodes(flag, k)
    test_days = max((tt.t.max() - tt.t.min()).total_seconds() / 86400, 1e-9)
    in_inc = np.zeros(len(tt), bool)
    for r in inc.itertuples():
        in_inc |= ((tt.t >= r.start) & (tt.t <= r.end)).to_numpy()
    false_eps = [e for e in eps if not in_inc[e[1]]]
    evaluable = [r for r in inc.itertuples() if r.start >= tt.t.min() and r.end <= tt.t.max()]
    detected, delays = 0, []
    for r in evaluable:
        hits = [e for e in eps if r.start <= tt.t[e[0]] <= r.end]
        if hits:
            detected += 1
            delays.append((tt.t[hits[0][0]] - r.start).total_seconds() / 60)
    out.update({"false_alerts_per_day": len(false_eps) / test_days, "incidents_evaluable": len(evaluable),
                "incidents_detected": detected, "median_detection_delay_min": float(np.median(delays)) if delays else None,
                "claim": "detection of an ongoing incident, not failure prediction"})
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--source", type=Path); a = ap.parse_args()
    cfg = load_config()
    src = a.source or Path(json.loads((resolve(cfg, "manifests") / "metropt3.json").read_text())["parquet_path"])
    r = run(cfg, src)
    (resolve(cfg, "results") / "metropt_mining.json").write_text(json.dumps(r, indent=2, default=str))
    print(json.dumps(r, indent=2, default=str))
