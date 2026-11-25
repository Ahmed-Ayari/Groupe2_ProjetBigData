"""Build disjoint calibration/test lots (by source bytes) from the manifest, and verify disjointness."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd

from .config import load_config, resolve


def lot_targets(cal_gb: list[float], test_gb: list[float]) -> list[tuple[str, str, float]]:
    targets = []
    for i in range(max(len(cal_gb), len(test_gb))):
        if i < len(cal_gb):
            targets.append((f"cal_{i + 1}", "calibration", float(cal_gb[i])))
        if i < len(test_gb):
            targets.append((f"test_{i + 1}", "test", float(test_gb[i])))
    return targets


def plan_lots(
    files: pd.DataFrame,
    cal_gb: list[float],
    test_gb: list[float],
    gap_files: int = 1,
    min_ratio: float = 4,
) -> dict[str, pd.DataFrame]:
    """Walk files in time order and cut consecutive lots, interleaving calibration and test targets.

    Lots never share a file; gaps are skipped. The largest lot in each split grows as needed to
    preserve the requested realized-byte ratio despite indivisible input files.
    """
    files = files.sort_values("start").reset_index(drop=True)
    lots, pos = {}, 0
    realized_sizes: dict[str, list[int]] = {}
    targets = lot_targets(cal_gb, test_gb)
    for target_i, (lot_id, split, gb) in enumerate(targets):
        target_bytes = gb * 2**30
        is_largest = not any(later_split == split for _, later_split, _ in targets[target_i + 1:])
        goal_bytes = target_bytes
        if is_largest and realized_sizes.get(split):
            goal_bytes = max(goal_bytes, min(realized_sizes[split]) * min_ratio)
        acc, rows = 0, []
        while pos < len(files) and acc < goal_bytes:
            rows.append(files.iloc[pos]); acc += int(files.iloc[pos].source_bytes); pos += 1
        if acc < target_bytes * 0.8:
            raise ValueError(f"not enough listed files for {lot_id} ({acc / 2**30:.2f} of {gb} GB)")
        if acc < goal_bytes:
            raise ValueError(
                f"not enough listed files for {lot_id} to meet the realized {min_ratio:g}:1 "
                f"size ratio ({acc / 2**30:.2f} of {goal_bytes / 2**30:.2f} GB)"
            )
        pos += gap_files
        df = pd.DataFrame(rows)
        df["lot_id"], df["split"] = lot_id, split
        lots[lot_id] = df
        realized_sizes.setdefault(split, []).append(acc)
    return lots


def ratio_ok(lots: dict[str, pd.DataFrame], split: str, min_ratio: float) -> bool:
    sizes = [d.source_bytes.sum() for d in lots.values() if d.split.iloc[0] == split]
    return max(sizes) / min(sizes) >= min_ratio


def check_disjoint(lots: dict[str, pd.DataFrame]) -> None:
    cal = set().union(*[set(d.local_path) for d in lots.values() if d.split.iloc[0] == "calibration"])
    tst = set().union(*[set(d.local_path) for d in lots.values() if d.split.iloc[0] == "test"])
    assert not (cal & tst), f"calibration/test overlap: {sorted(cal & tst)[:3]}"


def write_lots(cfg: dict) -> dict:
    man = resolve(cfg, "manifests")
    allm = pd.read_csv(man / "ukdale_all.csv")
    ratio = cfg["lots"]["min_ratio_extremes"]
    lots = plan_lots(allm, cfg["lots"]["calibration_gb"], cfg["lots"]["test_gb"], min_ratio=ratio)
    check_disjoint(lots)
    for s in ("calibration", "test"):
        assert ratio_ok(lots, s, ratio), f"{s} extremes ratio < {ratio}"
    (man / "lots").mkdir(parents=True, exist_ok=True)
    splits = {}
    for k, d in lots.items():
        d.to_csv(man / "lots" / f"{k}.csv", index=False)
        splits[k] = {"split": d.split.iloc[0], "files": len(d), "source_gb": round(d.source_bytes.sum() / 2**30, 3),
                     "first": float(d.start.iloc[0]), "last": float(d.start.iloc[-1])}
    (man / "splits.json").write_text(json.dumps(splits, indent=2))
    return splits


if __name__ == "__main__":
    argparse.ArgumentParser().parse_args()
    print(json.dumps(write_lots(load_config()), indent=2))
