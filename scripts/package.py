"""Create tests.zip (code, no raw data) and results.zip (measurements, figures, scripts)."""
import sys, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist"; OUT.mkdir(exist_ok=True)
SKIP = {"__pycache__", ".pytest_cache", ".venv", "data", "smoke", "dist", ".git", "out"}


def add(zf, p: Path):
    for f in (p.rglob("*") if p.is_dir() else [p]):
        if f.is_file() and not (set(f.relative_to(ROOT).parts) & SKIP) and f.suffix != ".pyc":
            zf.write(f, f.relative_to(ROOT))


with zipfile.ZipFile(OUT / "tests.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for n in ("src", "tests", "configs", "manifests", "environment", "scripts", "docs", "report", "README.md", "ASSUMPTIONS.md", "STATUS.md",
              "contributions.md", "requirements.txt", "pyproject.toml", "Makefile"):
        if (ROOT / n).exists(): add(z, ROOT / n)
with zipfile.ZipFile(OUT / "results.zip", "w", zipfile.ZIP_DEFLATED) as z:
    r = ROOT / "results"
    for n in ("runs.csv", "failed_runs.csv", "preparation_costs.csv", "decisions.json", "final_by_lot.csv", "final_summary.csv",
              "final_paired.csv", "metropt_mining.json", "figures", "equivalence", "eventlogs", "table_feasibility_failures.csv",
              "table_equivalence.csv", "table_preparation_cost.csv"):
        if (r / n).exists(): add(z, r / n)
    add(z, ROOT / "src" / "bigdata" / "plots.py")
print("wrote", OUT / "tests.zip", OUT / "results.zip")
