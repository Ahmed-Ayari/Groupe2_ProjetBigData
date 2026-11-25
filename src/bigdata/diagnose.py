"""docs/pilot_diagnosis.md from MEASURED pilot runs: phase attribution by differences between stop_after probes.

decode  = time to read+decode+reduce per file (noop sink)           [raw scope only]
compute = (compute probe) - (decode probe)  ~ shuffle + merge
write   = (write run)     - (compute probe)  ~ output write
Differences of medians over repetitions; with few repetitions treat them as indicative, not exact.
"""
from __future__ import annotations
import pandas as pd

from .config import ROOT, load_config, resolve


def main() -> None:
    cfg = load_config(); res = resolve(cfg, "results")
    r = pd.read_csv(res / "runs.csv", low_memory=False)
    r = r[(r.status == "OK") & (r.method == "PILOT") & (r.dataset == "ukdale") & (r.scope == "raw")].copy()
    r["duration_s"] = pd.to_numeric(r.duration_s)
    L = ["# Pilot diagnosis (generated from results/runs.csv, method=PILOT, UK-DALE, raw scope)", ""]
    if r.empty:
        L.append("not executed")
    else:
        m = r.groupby(["lot_id", "p", "stop_after"]).duration_s.median().unstack("stop_after")
        L += ["| lot | p | decode (s) | compute-decode (s) | write-compute (s) | total (s) | dominant phase |", "|---|---|---|---|---|---|---|"]
        for (lot, p), row in m.iterrows():
            d, c, w = row.get("decode"), row.get("compute"), row.get("write")
            if pd.isna(d) or pd.isna(c) or pd.isna(w):
                continue
            ph = {"read+decode": d, "shuffle/merge": max(c - d, 0), "write": max(w - c, 0)}
            L.append(f"| {lot} | {int(p)} | {d:.2f} | {c - d:.2f} | {w - c:.2f} | {w:.2f} | {max(ph, key=ph.get)} |")
        L += ["", "Interpretation (to be written by the author from the table above): if read+decode dominates, tuning P (shuffle partitions) "
              "can only have a small effect and the read partitioning Q becomes the relevant knob."]
    (ROOT / "docs" / "pilot_diagnosis.md").write_text("\n".join(L))
    print("docs/pilot_diagnosis.md written")


if __name__ == "__main__":
    main()
