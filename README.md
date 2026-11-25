# Projet Big Data M2 DSIR: joint choice of resources and partitioning (MetroPT-3, UK-DALE)

Code, tests and a reproducible experiment pipeline. **No result is included before you run the campaigns on your machine**:
everything in the report must come from `results/runs.csv`. Read `ASSUMPTIONS.md` and `STATUS.md` first.

## 0. Requirements
Python 3.10+, Java 17 or 21 (for PySpark), 16 GB RAM, 4 cores, 50 GB free SSD.

```bash
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
make setup                                               # pip install -r requirements.txt
make env                                                 # writes environment/hardware.json and versions.txt
make test                                                # unit + equivalence tests on synthetic data (about 1 min)
make smoke                                               # whole pipeline on a tiny synthetic dataset (to see it work)
```
Windows without `make`: run the commands of the Makefile by hand (they are one-liners; set `PYTHONPATH=src`).

## 1. Real data (run in this order)
```bash
# MetroPT-3: download, hash, audit (docs/audit_metropt3.md), Parquet conversion
make metropt

# UK-DALE house_1: start with one week (do NOT list/download everything: 7.6 TB overall)
make ukdale-list WEEKS="2013/wk11"
make lots                      # disjoint calibration/test lots (needs all configured lot volumes plus gap files)
python -m bigdata.acquire ukdale-download --lots cal_1 --dry-run     # check first
make download                  # downloads files lot by lot, SHA-256, disk guard (stops under 10 GB free)

# MANDATORY CHECK before any benchmark (channel order, scaling, timestamps):
python -m bigdata.ukdale verify data/raw/ukdale/house_1/<year>/<wk>/<file>.flac --cal data/raw/ukdale/calibration_house_1.cfg
```
Listing pages are read from CEDA's browse host; file sizes and downloads use its `dap` host. Listings are cached in
`manifests/ukdale_listing_cache.json`. At most 500 files are checked by default, in timestamp order, and listing stops
once the configured lots can be formed. If one week is insufficient, add weeks or raise `MAX_FILES`.
If no `.flac` links are parsed, inspect the response with
`python -m bigdata.acquire ukdale-debug --week 2013/wk11`. For a JavaScript-rendered listing, save the `.flac` URLs
copied from the browser, one per line, and run `make ukdale-list FILELIST=path/to/urls.txt`.

## 2. Campaigns (sequential, unattended; never run two at once)
```bash
make pilot                     # B0 vs Spark p=1,2,4, phase probes, 3 reps; writes docs/pilot_diagnosis.md
make grid                      # p x P sweep at one calibration lot + AQE off + range strategy + Q sweep
make sizeup-cal P=64           # size-up / Q1 on calibration lots (choose P from the grid results)
make fit                       # model comparison (grouped CV), margin, deadlines, decisions.json  (calibration lots only)
make sizeup-test P=64 && make final   # held-out lots: B0, B1, B2, B3, B4, B4 without margin; 5 repetitions
make evaluate                  # hit rate, cost, paired ratios, bootstrap
make mining                    # IsolationForest on MetroPT-3 (UCI incident intervals; ongoing-incident detection only)
make plots                     # figures + tables + docs/report_facts.md
make package                   # dist/tests.zip and dist/results.zip
```
`python -m bigdata.campaign <name> --budget-only` prints the number of runs and the worst-case duration before launching.
Runs are resumable (completed `run_id`s are skipped) and randomised with a fixed seed. Time out runs are logged as `TIMEOUT`
(censored, never successes); every failure stays in `results/runs.csv` and `results/failed_runs.csv`.

## 3. Layout
`src/bigdata/` windows, ukdale, local_ref (B0), spark_jobs, runner, metrics, selector, mining, plots, acquire, audit, lots, campaign.
`configs/` single source of parameters. `manifests/` data, lots, splits. `results/` raw measures. `tests/` pytest.

## 4. Method map
B0 local chunked Python; B1 Spark `local[1]`; B2 frozen fixed (p,P) chosen on calibration; B3 resources-only selection (P fixed to B2's);
B4 joint (p,P) selection; ablation B4 vs B3 and B4 without margin. All use the same AQE policy, outputs and tolerances (equivalence-checked
against B0 on every run: `results/equivalence/*.json`).
