"""docs/report_facts.md: every key number with its source file and filter, so the report cites measurements only."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

from .config import ROOT, load_config, resolve


def main() -> None:
    cfg = load_config(); res = resolve(cfg, "results")
    runs = pd.read_csv(res / "runs.csv", low_memory=False)
    L = ["# Report facts (auto-generated; every number comes from the listed file)", ""]
    hw = ROOT / "environment" / "hardware.json"
    if hw.exists():
        L += ["## Hardware (environment/hardware.json)", "```", hw.read_text(), "```", ""]
    L += ["## Runs by method and status (results/runs.csv, group by method,status)", "", "| method | status | n |", "|---|---|---|"]
    for (m, s), n in runs.groupby(["method", "status"]).size().items():
        L.append(f"| {m} | {s} | {n} |")
    ok = runs[(runs.status == "OK") & (runs.stop_after == "write")].copy()
    ok["duration_s"] = pd.to_numeric(ok.duration_s, errors="coerce")
    L += ["", "## Median / min / max duration_s (s) per dataset, method, p, scope (filter: status=OK, stop_after=write)", "",
          "| dataset | method | p | scope | lot | n | median | min | max |", "|---|---|---|---|---|---|---|---|---|"]
    for k, g in ok.groupby(["dataset", "method", "p", "scope", "lot_id"]):
        L.append("| " + " | ".join(map(str, k)) + f" | {len(g)} | {g.duration_s.median():.2f} | {g.duration_s.min():.2f} | {g.duration_s.max():.2f} |")
    for name in ("decisions.json", "final_summary.csv", "final_paired.csv", "metropt_mining.json", "preparation_costs.csv"):
        f = res / name
        if f.exists():
            body = f.read_text()
            if name == "decisions.json":
                d = json.loads(body); body = json.dumps({k: d[k] for k in ("model", "cv", "margin_s", "B2", "n_calibration_runs", "fit_and_select_seconds", "calibration_cost_s")}, indent=2)
            L += ["", f"## results/{name}", "```", body[:6000], "```"]
        else:
            L += ["", f"## results/{name}", "not executed / not available"]
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "report_facts.md").write_text("\n".join(L))
    print("docs/report_facts.md written")


if __name__ == "__main__":
    main()
