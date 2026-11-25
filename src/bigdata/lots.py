"""Build disjoint calibration/test lots (by source bytes) from the manifest, and verify disjointness."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd

from .config import load_config, resolve


def plan_lots(files: pd.DataFrame, cal_gb: list[float], test_gb: list[float], gap_files: int = 1) -> dict[str, pd.DataFrame]:
    """Walk files in time order and cut consecutive lots, interleaving calibration and test targets.

    Lots never share a file; `gap_files` unused files are skipped between lots so that periods are separated.
    """
    files = files.sort_values("start").reset_index(drop=True)
    order = []
    for i in range(max(len(cal_gb), len(test_gb))):
        if i < len(cal_gb): order.append((f"cal_{i + 1}", "calibration", cal_gb[i]))
        if i < len(test_gb): order.append((f"test_{i + 1}", "test", test_gb[i]))
    lots, pos = {}, 0
    for lot_id, split, gb in order:
        acc, rows = 0, []
        while pos < len(files) and acc < gb * 2**30:
            rows.append(files.iloc[pos]); acc += int(files.iloc[pos].source_bytes); pos += 1
        if acc < gb * 2**30 * 0.8:
            raise ValueError(f"not enough listed files for {lot_id} ({acc / 2**30:.2f} of {gb} GB)")
        pos += gap_files
        df = pd.DataFrame(rows)
        df["lot_id"], df["split"] = lot_id, split
        lots[lot_id] = df
    return lots


def ratio_ok(lots: dict[str, pd.DataFrame], split: str, min_ratio: float) -> bool:
    sizes = [d.source_bytes.sum() for d in lots.values() if d.split.iloc[0] == split]
    return max(sizes) / min(sizes) >= min_ratio * 0.9


def check_disjoint(lots: dict[str, pd.DataFrame]) -> None:
    cal = set().union(*[set(d.local_path) for d in lots.values() if d.split.iloc[0] == "calibration"])
    tst = set().union(*[set(d.local_path) for d in lots.values() if d.split.iloc[0] == "test"])
    assert not (cal & tst), f"calibration/test overlap: {sorted(cal & tst)[:3]}"


def write_lots(cfg: dict) -> dict:
    man = resolve(cfg, "manifests")
    allm = pd.read_csv(man / "ukdale_all.csv")
    lots = plan_lots(allm, cfg["lots"]["calibration_gb"], cfg["lots"]["test_gb"])
    check_disjoint(lots)
    (man / "lots").mkdir(parents=True, exist_ok=True)
    splits = {}
    for k, d in lots.items():
        d.to_csv(man / "lots" / f"{k}.csv", index=False)
        splits[k] = {"split": d.split.iloc[0], "files": len(d), "source_gb": round(d.source_bytes.sum() / 2**30, 3),
                     "first": float(d.start.iloc[0]), "last": float(d.start.iloc[-1])}
    (man / "splits.json").write_text(json.dumps(splits, indent=2))
    for s in ("calibration", "test"):
        assert ratio_ok(lots, s, cfg["lots"]["min_ratio_extremes"]), f"{s} extremes ratio < {cfg['lots']['min_ratio_extremes']}"
    return splits


if __name__ == "__main__":
    argparse.ArgumentParser().parse_args()
    print(json.dumps(write_lots(load_config()), indent=2))
