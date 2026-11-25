"""Configuration selector: predict T(V, p, P, z) on calibration lots, pick (p, P) minimizing p*T_hat s.t. T_hat + margin <= D.

Features are known BEFORE execution (volume, file-size statistics, p, P). Shuffle/spill from the same run are never used.
Model choice and margin use grouped cross-validation (groups = lot_id) on calibration lots ONLY.
Test lots are only read to compute their feature vector (size) and deadlines, never their durations.
"""
from __future__ import annotations
import argparse, json, time
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GroupKFold
from sklearn.tree import DecisionTreeRegressor

from .config import load_config, resolve


# ----------------------------------------------------------------------------- data ------------
def lot_features(cfg: dict) -> pd.DataFrame:
    man = resolve(cfg, "manifests")
    rows = []
    for f in sorted((man / "lots").glob("*.csv")):
        d = pd.read_csv(f)
        rows.append({"lot_id": f.stem, "V": float(d.source_bytes.sum()), "n_files": len(d),
                     "mean_file": float(d.source_bytes.mean()), "std_file": float(d.source_bytes.std(ddof=0))})
    return pd.DataFrame(rows)


def calibration_table(runs: pd.DataFrame, feats: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Admissible calibration runs: UK-DALE, treatment A, raw scope, Spark, full write, correct output, split=calibration."""
    r = runs[(runs.dataset == "ukdale") & (runs.workload == "A") & (runs.scope == "raw") & (runs.engine == "spark")
             & (runs.stop_after == "write") & (runs.status == "OK") & (runs.output_check == "ok")
             & (runs.split == "calibration") & (runs.AQE == 1) & (runs.strategy == "hash")]
    r = r[r.method.isin(["GRID", "SIZEUP", "B1", "PILOT"])]
    t = r.merge(feats, on="lot_id")
    t = t.rename(columns={"duration_s": "T"})
    t["P"] = t.P_initial.astype(float)
    return t[["run_id", "lot_id", "V", "n_files", "mean_file", "std_file", "p", "P", "T"]].reset_index(drop=True)


# ----------------------------------------------------------------------------- models ----------
def X_loglin(d: pd.DataFrame) -> np.ndarray:
    lp = np.log(d.P.to_numpy(float))
    return np.column_stack([np.log(d.V), np.log(d.p.astype(float)), lp, lp ** 2])


class RuleModel:
    """T = V / throughput(p) with throughput the median observed V/T for each p (nearest p if unseen). P is ignored."""
    name = "rule_volume"

    def fit(self, d):
        self.thr = (d.V / d["T"]).groupby(d.p).median().to_dict()
        return self

    def predict(self, d):
        ps = np.array(sorted(self.thr))
        return np.array([r.V / self.thr[ps[np.abs(ps - r.p).argmin()]] for r in d.itertuples()])


class LogLinModel:
    name = "loglinear"

    def fit(self, d):
        self.m = LinearRegression().fit(X_loglin(d), np.log(d["T"]))
        return self

    def predict(self, d):
        return np.exp(self.m.predict(X_loglin(d)))


class TreeModel:
    name = "tree_depth<=3"

    def __init__(self, depth=3):
        self.depth = depth

    def fit(self, d):
        self.m = DecisionTreeRegressor(max_depth=self.depth, min_samples_leaf=2, random_state=0).fit(self._x(d), np.log(d["T"]))
        return self

    @staticmethod
    def _x(d):
        return np.column_stack([d.V, d.p, d.P, d.n_files])

    def predict(self, d):
        return np.exp(self.m.predict(self._x(d)))


def grouped_cv(d: pd.DataFrame, depth: int) -> dict[str, dict]:
    """Out-of-fold predictions with groups = lot_id (all repetitions of a lot stay together)."""
    n_groups = d.lot_id.nunique()
    if n_groups < 3:
        raise ValueError(f"need >=3 calibration lots for grouped CV, have {n_groups}")
    out = {}
    for mk in (RuleModel, LogLinModel, lambda: TreeModel(depth)):
        oof = np.full(len(d), np.nan)
        for tr, va in GroupKFold(n_splits=min(n_groups, 5)).split(d, groups=d.lot_id):
            m = mk().fit(d.iloc[tr])
            oof[va] = m.predict(d.iloc[va])
        name = mk().name
        res = d["T"].to_numpy() - oof
        out[name] = {"mape": float(np.mean(np.abs(res) / d["T"])), "mae_s": float(np.mean(np.abs(res))), "oof": oof, "resid": res, "factory": mk}
    return out


# ----------------------------------------------------------------------------- decisions -------
def candidates(cfg: dict) -> pd.DataFrame:
    return pd.DataFrame([(p, P) for p in cfg["spark"]["p_values"] for P in cfg["spark"]["P_values"]], columns=["p", "P"])


def choose(model, lot_row: pd.Series, D: float, margin: float, cands: pd.DataFrame, fix_P: int | None = None) -> dict:
    """Minimize p * T_hat subject to T_hat + margin <= D. Returns an explicit infeasible decision if none qualifies."""
    c = cands if fix_P is None else cands[cands.P == fix_P]
    d = c.assign(V=lot_row.V, n_files=lot_row.n_files, mean_file=lot_row.mean_file, std_file=lot_row.std_file)
    d["T_hat"] = model.predict(d)
    ok = d[d.T_hat + margin <= D]
    if ok.empty:
        return {"feasible": False, "T_hat_min": float(d.T_hat.min())}
    best = ok.assign(cost=ok.p * ok.T_hat).sort_values(["cost", "T_hat"]).iloc[0]
    return {"feasible": True, "p": int(best.p), "P": int(best.P), "T_hat": float(best.T_hat), "cost_hat": float(best.cost)}


def deadlines(cal: pd.DataFrame, feats: pd.DataFrame, cfg: dict, lots: list[str]) -> dict:
    """D(lot, scenario) = V / quantile_q(calibration throughput). Defined from calibration only, before any test run."""
    thr = cal.V / cal["T"]
    out = {}
    for sc, q in cfg["selector"]["deadline_scenarios"].items():
        thr_q = float(np.quantile(thr, 1 - q))      # q=0.8 -> demanding: only fast (high-throughput) configs qualify
        out[sc] = {"throughput_Bps": thr_q, **{l: float(feats.set_index("lot_id").loc[l, "V"] / thr_q) for l in lots}}
    return out


def frozen_config_b2(cal: pd.DataFrame, D_cal: dict, cfg: dict, scenario: str) -> dict:
    """B2: the single fixed (p, P) that meets the most calibration deadlines, ties by lowest median cost; then frozen."""
    g = cal.groupby(["p", "P", "lot_id"])["T"].median().reset_index()
    g["D"] = g.lot_id.map(D_cal[scenario])
    g["hit"] = g["T"] <= g["D"]
    s = g.groupby(["p", "P"]).agg(hits=("hit", "sum"), cost=("T", lambda x: float(np.median(x))))
    s["cost"] = [r.cost * idx[0] for idx, r in s.iterrows()]
    best = s.sort_values(["hits", "cost"], ascending=[False, True]).index[0]
    return {"p": int(best[0]), "P": int(best[1])}


def fit_and_decide(cfg: dict) -> dict:
    t_start = time.perf_counter()
    res = resolve(cfg, "results")
    runs = pd.read_csv(res / "runs.csv")
    feats = lot_features(cfg)
    split = json.loads((resolve(cfg, "manifests") / "splits.json").read_text())
    cal = calibration_table(runs, feats, cfg)
    cv = grouped_cv(cal, cfg["selector"]["max_depth"])
    best_name = min(cv, key=lambda k: cv[k]["mape"])
    model = cv[best_name]["factory"]().fit(cal)
    pos = cv[best_name]["resid"][cv[best_name]["resid"] > 0]
    margin = float(np.quantile(pos, cfg["selector"]["margin_quantile"])) if len(pos) else 0.0   # additive, seconds, from VALIDATION residuals
    test_lots = sorted(k for k, v in split.items() if v["split"] == "test")
    cal_lots = sorted(cal.lot_id.unique())
    D = deadlines(cal, feats, cfg, test_lots + cal_lots)
    cands = candidates(cfg)
    decisions, b2 = [], {}
    for sc in D:
        b2[sc] = frozen_config_b2(cal, D, cfg, sc)
    for sc in D:
        fixP = cfg["selector"]["fixed_P_for_b3"] or b2[sc]["P"]
        for lot in test_lots:
            row = feats.set_index("lot_id").loc[lot]
            Dl = D[sc][lot]
            for method, kw in (("B3", dict(margin=margin, fix_P=fixP)), ("B4", dict(margin=margin)), ("B4_nomargin", dict(margin=0.0))):
                dec = choose(model, row, Dl, cands=cands, **kw)
                decisions.append({"lot": lot, "scenario": sc, "deadline_s": Dl, "method": method, **dec})
            one = pd.DataFrame([{"p": b2[sc]["p"], "P": b2[sc]["P"], "V": row.V, "n_files": row.n_files,
                                 "mean_file": row.mean_file, "std_file": row.std_file}])
            decisions.append({"lot": lot, "scenario": sc, "deadline_s": Dl, "method": "B2", "feasible": True,
                              **b2[sc], "T_hat": float(model.predict(one)[0])})
    out = {
        "model": best_name, "cv": {k: {"mape": v["mape"], "mae_s": v["mae_s"]} for k, v in cv.items()},
        "margin_s": margin, "margin_quantile": cfg["selector"]["margin_quantile"], "n_calibration_runs": int(len(cal)),
        "calibration_lots": cal_lots, "B2": b2.get("moderate", next(iter(b2.values()))), "B2_by_scenario": b2,
        "deadlines": D, "decisions": decisions, "fit_and_select_seconds": time.perf_counter() - t_start,
        "calibration_cost_s": float(runs[runs.run_id.isin(cal.run_id)].submit_duration_s.sum()),
    }
    # guard: no test lot may appear in the calibration table
    assert not (set(cal.lot_id) & set(test_lots)), "test lot leaked into calibration"
    (res / "decisions.json").write_text(json.dumps(out, indent=2))
    return out


# ----------------------------------------------------------------------------- evaluation ------
def paired_bootstrap(ratios: np.ndarray, n: int = 5000, seed: int = 0) -> tuple[float, float]:
    """Percentile bootstrap over lots of the mean paired ratio. With few lots the interval is wide: state it."""
    rng = np.random.default_rng(seed)
    if len(ratios) == 0:
        return (float("nan"), float("nan"))
    m = [rng.choice(ratios, len(ratios)).mean() for _ in range(n)]
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def evaluate(cfg: dict) -> pd.DataFrame:
    """Deadline hit rate (failures, timeouts and infeasible decisions count in the denominator), cost, paired ratios."""
    res = resolve(cfg, "results")
    runs = pd.read_csv(res / "runs.csv")
    dec = json.loads((res / "decisions.json").read_text())
    rows = []
    t = runs[(runs.split == "test") & (runs.dataset == "ukdale") & (runs.workload == "A") & (runs.scope == "raw")]
    for d in dec["decisions"]:
        sub = t[(t.method == d["method"]) & (t.lot_id == d["lot"]) & (t.policy == d["scenario"])]
        if not d["feasible"]:
            rows.append({**{k: d[k] for k in ("lot", "scenario", "method", "deadline_s")}, "n": 1, "hits": 0, "infeasible": 1, "median_T": np.nan, "cost": np.nan})
            continue
        ok = sub[sub.status == "OK"]
        hits = int((ok.duration_s <= d["deadline_s"]).sum())
        rows.append({**{k: d[k] for k in ("lot", "scenario", "method", "deadline_s")}, "n": len(sub), "hits": hits, "infeasible": 0,
                     "median_T": float(ok.duration_s.median()) if len(ok) else np.nan,
                     "cost": float((ok.duration_s * ok.p).median() / 60) if len(ok) else np.nan,
                     "T_hat": d.get("T_hat"), "p": d["p"], "P": d["P"]})
    df = pd.DataFrame(rows)
    df.to_csv(res / "final_by_lot.csv", index=False)
    summ = []
    for (sc, m), g in df.groupby(["scenario", "method"]):
        summ.append({"scenario": sc, "method": m, "hit_rate": g.hits.sum() / g.n.sum(), "runs_or_decisions": int(g.n.sum()),
                     "infeasible": int(g.infeasible.sum()), "median_cost_core_min": g.cost.median()})
    s = pd.DataFrame(summ)
    pr = []
    for sc in df.scenario.unique():
        a = df[(df.scenario == sc) & (df.method == "B4")].set_index("lot").cost
        b = df[(df.scenario == sc) & (df.method == "B3")].set_index("lot").cost
        r = (a / b).dropna().to_numpy()
        lo, hi = paired_bootstrap(r)
        pr.append({"scenario": sc, "comparison": "cost B4/B3 (paired by lot)", "mean_ratio": float(r.mean()) if len(r) else np.nan,
                   "ci_low": lo, "ci_high": hi, "n_lots": len(r), "ci_method": "percentile bootstrap over lots, 5000 resamples; wide with few lots; not a coverage guarantee"})
    s.to_csv(res / "final_summary.csv", index=False)
    pd.DataFrame(pr).to_csv(res / "final_paired.csv", index=False)
    return s


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fit", "evaluate"])
    a = ap.parse_args()
    cfg = load_config()
    if a.cmd == "fit":
        o = fit_and_decide(cfg)
        print(json.dumps({k: o[k] for k in ("model", "cv", "margin_s", "B2", "n_calibration_runs")}, indent=2))
    else:
        print(evaluate(cfg).to_string())
