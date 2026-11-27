"""Expanding-window anomaly detection evaluation for verified MetroPT-3 incidents.

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


def _false_alert_threshold(scores: np.ndarray, k: int, budget: float, validation_days: float) -> tuple[float, float]:
    for q in np.linspace(0.90, 0.9999, 400):
        threshold = float(np.quantile(scores, q))
        rate = len(episodes(scores > threshold, k)) / validation_days
        if rate <= budget:
            return threshold, rate
    return float(np.max(scores)) + np.finfo(float).eps, 0.0


def evaluate_incidents(df: pd.DataFrame, X: pd.DataFrame, incidents: pd.DataFrame, cfg: dict) -> dict:
    """Fit independently before each incident; validate on its preceding normal day."""
    k = int(cfg["mining"]["k_consecutive"])
    budget = float(cfg["mining"]["false_alert_budget_per_day"])
    incident_mask = pd.Series(False, index=df.index)
    for incident in incidents.itertuples():
        incident_mask |= (df.t >= incident.start) & (df.t <= incident.end)

    per_incident, scored = [], []
    false_alert_total = 0
    normal_days_total = 0.0
    for idx, incident in enumerate(incidents.itertuples(), 1):
        validation_start = incident.start - pd.Timedelta(days=1)
        training = (df.t < validation_start) & ~incident_mask
        validation = (df.t >= validation_start) & (df.t < incident.start) & ~incident_mask
        test_start, test_end = incident.start - pd.Timedelta(days=1), incident.end + pd.Timedelta(days=1)
        test = (df.t >= test_start) & (df.t <= test_end)
        if int(training.sum()) < 2 or int(validation.sum()) < k or int(test.sum()) == 0:
            raise ValueError(f"insufficient history or validation data for incident {idx} ({incident.start})")

        scaler = StandardScaler().fit(X.loc[training])
        iso = IsolationForest(n_estimators=200, contamination=cfg["mining"]["contamination"],
                              random_state=cfg["run"]["seed"]).fit(scaler.transform(X.loc[training]))
        validation_score = -iso.score_samples(scaler.transform(X.loc[validation]))
        validation_days = max((df.loc[validation, "t"].max() - df.loc[validation, "t"].min()).total_seconds() / 86400, 1e-9)
        threshold, validation_false_rate = _false_alert_threshold(validation_score, k, budget, validation_days)

        test_df = df.loc[test].copy()
        test_scores = -iso.score_samples(scaler.transform(X.loc[test]))
        test_df["score"] = test_scores
        flag = test_scores > threshold
        eps = episodes(flag, k)
        inside = ((test_df.t >= incident.start) & (test_df.t <= incident.end)).to_numpy()
        hits = [episode for episode in eps if incident.start <= test_df.t.iloc[episode[0]] <= incident.end]
        detected = bool(hits)
        delay = ((test_df.t.iloc[hits[0][0]] - incident.start).total_seconds() / 60) if detected else None
        outside = [episode for episode in eps if not inside[episode[1]]]
        incident_days = max((incident.end - incident.start).total_seconds() / 86400, 0.0)
        outside_days = max((test_df.t.max() - test_df.t.min()).total_seconds() / 86400 - incident_days, 1e-9)
        false_per_day = len(outside) / outside_days
        false_alert_total += len(outside)
        normal_days_total += outside_days
        per_incident.append({
            "incident": idx, "start": incident.start.isoformat(), "end": incident.end.isoformat(),
            "detected": detected, "detection_delay_min": delay,
            "false_alerts_outside_incident": len(outside), "false_alerts_per_day_outside_incident": false_per_day,
            "validation_false_alerts_per_day": validation_false_rate,
            "validation_false_alert_budget_per_day": budget, "threshold": threshold,
            "training_windows": int(training.sum()), "validation_windows": int(validation.sum()),
            "test_windows": int(test.sum()),
        })
        test_df["incident"] = idx
        scored.append(test_df[["equipment_id", "window_id", "t", "score", "incident"]])

    delays = [r["detection_delay_min"] for r in per_incident if r["detected"]]
    return {
        "evaluation": "expanding-window ongoing-incident detection; not failure prediction",
        "incidents_evaluable": len(per_incident), "incidents_detected": sum(r["detected"] for r in per_incident),
        "detection_rate": sum(r["detected"] for r in per_incident) / len(per_incident),
        "median_detection_delay_min": float(np.median(delays)) if delays else None,
        "false_alerts_per_day_outside_incidents": false_alert_total / normal_days_total,
        "incidents": per_incident,
        "note": ("The first incident (18 Apr) has about 18,000 windows available for training. "
                 "Each threshold is tuned on about one day of validation data, so results are indicative only."),
        "claim": "detection of an ongoing incident only, never prediction",
        "scored_windows": pd.concat(scored, ignore_index=True),
    }


def run(cfg: dict, source: Path) -> dict:
    df = features(cfg, source)
    num = [c for c in df.columns if c.endswith(("__mean", "__max", "__std_pop")) or c.startswith(("delta_", "hist_"))] + ["prev_missing"]
    X = df[num].fillna(0.0)
    incident_path = Path(cfg["mining"]["incidents"])
    if not incident_path.is_absolute():
        incident_path = ROOT / incident_path
    inc = load_incidents(incident_path)
    out = {"n_features": len(num), "k_consecutive": cfg["mining"]["k_consecutive"]}
    if inc is None:
        out["evaluation"] = (f"STOPPED: {incident_path} is missing or not verified "
                             "(start,end,label,verified=yes); no incident dates are invented by this code.")
        resolve(cfg, "results").mkdir(parents=True, exist_ok=True)
        return out
    evaluation = evaluate_incidents(df, X, inc, cfg)
    scored = evaluation.pop("scored_windows")
    out.update(evaluation)
    scored.to_parquet(resolve(cfg, "results") / "metropt_scores.parquet", index=False)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--source", type=Path); a = ap.parse_args()
    cfg = load_config()
    src = a.source or Path(json.loads((resolve(cfg, "manifests") / "metropt3.json").read_text())["parquet_path"])
    r = run(cfg, src)
    (resolve(cfg, "results") / "metropt_mining.json").write_text(json.dumps(r, indent=2, default=str))
    print(json.dumps(r, indent=2, default=str))
