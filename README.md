# Projet Big Data M2 DSIR: joint choice of resources and partitioning (MetroPT-3, UK-DALE)

Code, tests and a reproducible experiment pipeline. **Do not report benchmark findings until you run the campaigns on your
machine**; performance measurements are recorded in `results/runs.csv`. Read `ASSUMPTIONS.md` and `STATUS.md` first.

## 0. Requirements
Python 3.10+, Java 17 or 21 (recommended for PySpark), 16 GB RAM, 4 cores, and 50 GB free SSD are recommended for real campaigns.

```bash
python -m venv .venv
source .venv/bin/activate
export PYTHONPATH=src                                     # needed for direct `python -m bigdata...` commands below
make setup                                                # installs requirements.txt
make env                                                  # writes environment/hardware.json and versions.txt
make test                                                 # unit and equivalence tests, using synthetic data
make smoke                                                # compact synthetic campaign pipeline, not the full project
```
PowerShell setup without GNU make:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "src"
python -m pip install -r requirements.txt
python -m bigdata.runner --env
python -m pytest tests -q
```

To run the smoke target without GNU make in PowerShell:

```powershell
$env:BIGDATA_CONFIG = "configs/smoke.yaml"
python scripts/make_smoke_data.py
python -m bigdata.campaign pilot --lot cal_1
python -m bigdata.campaign grid --lot cal_2
python -m bigdata.campaign sizeup-cal --P 16
python -m bigdata.selector fit
python -m bigdata.campaign final
python -m bigdata.selector evaluate
Remove-Item Env:BIGDATA_CONFIG
```

Only setup and smoke have complete PowerShell command sequences above. The other `make` examples below require GNU make
(for example, in WSL), unless you invoke the corresponding Python modules with `PYTHONPATH=src` (PowerShell:
`$env:PYTHONPATH = "src"`). The sequential campaign runner is also available as `scripts/run_all.ps1`.

## 1. Real data (run in this order)
```bash
# MetroPT-3: download, hash, audit (docs/audit_metropt3.md), Parquet conversion
make metropt

# UK-DALE house_1: start with one week; do not mirror the full archive
# CEDA's live version_0 summary reported 4.0 TB and 24,941 files when checked 2026-11-25.
make ukdale-list WEEKS="2013/wk11"
make lots                      # disjoint calibration/test lots (needs all configured lot volumes plus gap files)
python -m bigdata.acquire ukdale-download --lots cal_1 --dry-run  # previews the cfg and cal_1 FLAC downloads
make download                  # downloads all six lots plus cfg; SHA-256, disk guard (stops under 10 GB free)

# MANDATORY CHECK before any benchmark (channel order, scaling, timestamps):
FILE=data/raw/ukdale/house_1/2013/wk11/vi-1363392000_236972.flac
python -m bigdata.ukdale verify "$FILE" --cal data/raw/ukdale/calibration_house_1.cfg
```
Listing pages are read from CEDA's browse host; file sizes and downloads use its `dap` host. Listings are cached in
`manifests/ukdale_listing_cache.json`. At most the first 500 links are eligible for HEAD sizing by default, in timestamp
order. Every requested week page is fetched/cached, but HEAD requests stop once the configured lots can be formed.
If one week is insufficient, add weeks (for example `WEEKS="2013/wk11 2013/wk12"`) or raise `MAX_FILES`.
Files are indivisible, so the largest lot in each split may exceed its configured target to keep the
realized source-byte ratio at or above 4:1.
If no `.flac` links are parsed, inspect the response with
`python -m bigdata.acquire ukdale-debug --week 2013/wk11`. For a JavaScript-rendered listing, save the `.flac` URLs
copied from the browser, one per line, and run `make ukdale-list FILELIST=path/to/urls.txt`.

## 2. Campaigns (sequential, unattended; never run two at once)
After data acquisition, lot creation, and verification, run the first pilot. Then check pending-run budgets before
starting the grid/final work:

```bash
make pilot
python -m bigdata.campaign pilot --budget-only
python -m bigdata.campaign grid --budget-only
python -m bigdata.campaign final --budget-only
```

Budget-only commands print pending run counts and timeout-based upper bounds, and use logged runtime estimates when
available. They do not prepare data or launch experiments. Before `fit` creates `results/decisions.json`,
`final --budget-only` reports a conservative upper bound assuming all selector decisions are feasible; rerun it after
`make fit` for the exact final plan. Sum the logged-runtime estimates for the 24-hour gate; already completed pilot
time is not part of the pending-run estimate.

If the combined estimate exceeds 24 hours, reduce in this order before launching affected experiments: (1) grid
repetitions (`run.repetitions_grid`) from 3 to 2; (2) in `grid_specs` in `src/bigdata/campaign.py`, omit
`GRID_AQEOFF` and `GRID_STRAT` at the two largest `P` values; (3) final repetitions
(`run.repetitions_final`) from 5 to 3. Size-up repetitions are separately controlled by `run.repetitions_sizeup`
and remain at 3. The last reduction is below the guide's requested minimum of 5 and must be disclosed. Record any
reductions in `ASSUMPTIONS.md` and `STATUS.md`.

Run the manual stages below, or after the budget gate use `bash scripts/run_all.sh` (PowerShell:
`.\scripts\run_all.ps1`). The script logs to `logs/`, resumes completed run IDs, and selects `P` from the grid.
It does not run MetroPT mining; run `make mining` separately. Do not run the script concurrently with any Spark job.

```bash
make grid                      # p x P sweep at one calibration lot + AQE off + range strategy + Q sweep
P=64                           # replace with the P selected from the grid results
make sizeup-cal P="$P"         # size-up / Q1 on calibration lots
make fit                       # model comparison (grouped CV), margin, deadlines, decisions.json  (calibration lots only)
make sizeup-test P="$P" && make final   # held-out lots; final uses 5 repetitions
make evaluate                  # hit rate, cost, paired ratios, bootstrap
make mining                    # IsolationForest on MetroPT-3; ongoing-incident detection only
make plots                     # figures + tables + docs/report_facts.md
make package                   # dist/tests.zip and dist/results.zip
```
With the current chronological split, the four verified incident intervals are in train/validation, not test.
`make mining` therefore reports zero test incidents evaluable; it cannot establish held-out incident detection performance.
The initial `make pilot` runs B0 vs Spark p=1,2,4 with phase probes and 3 repetitions, then runs `bigdata.diagnose` to write
`docs/pilot_diagnosis.md`. Runs are randomized with a fixed seed; completed `OK`, `TIMEOUT`, and
`EQUIV_FAIL` run IDs are skipped on resume, while ordinary errors can be retried. Timeouts are censored, never successes;
every non-OK run is recorded in both `results/runs.csv` and `results/failed_runs.csv`.

## 3. Layout
`src/bigdata/` windows, ukdale, local_ref (B0), spark_jobs, runner, metrics, selector, mining, plots, acquire, audit, lots, campaign.
`configs/` single source of parameters. `manifests/` data, lots, splits. `results/` raw measures. `tests/` pytest.

## 4. Method map
B0 local chunked Python; B1 Spark `local[1]`; B2 frozen fixed (p,P) chosen on calibration; B3 resources-only selection (P fixed to B2's);
B4 joint (p,P) selection; ablations compare B4 vs B3, B4 without margin, AQE off, and range partitioning. Main comparisons
hold the AQE policy fixed; the AQE-off sweep is explicit. Completed write runs are checked against B0 where a reference
exists; equivalence reports are in `results/equivalence/*.json`.
