# STATUS (updated 2026-11-25; real results are never inferred from smoke data)

| Step | State |
|---|---|
| Code, configs, runner, selector, mining, plots, packaging | Written; `scripts/run_all.sh` added; PowerShell runner added but not executed (`pwsh` unavailable). |
| Acquisition parser/retry tests | Covered by the full suite; fixture matches the live CEDA anchor and filename format; mocked HTTP 503→200 retry passes. |
| Full tests | 31 passed; 2 PySpark warnings that pandas >=3 is not fully supported. |
| Synthetic smoke pipeline | `make smoke` passed. Smoke data was regenerated, but all campaign run IDs were already present and skipped; selector outputs used existing synthetic results, not project findings. |
| MetroPT-3 | Download, audit, and Parquet preparation completed on 2026-11-25; 1,516,948 rows; 0 duplicate rows/timestamps; 0 duplicates removed. |
| UK-DALE listing and lots | `2013/wk11` listed successfully; 38 files sized (7.080 GiB). Six disjoint lots built; realized calibration and test extreme ratios are both >=4:1. |
| UK-DALE download/calibration verification | Downloaded the calibration config and one 197,105,625-byte FLAC. Verified PCM_24, channel 0 voltage RMS 243.404 V, channel 1 6.737 V, and `int_shift_bits: 0`; `auto` was wrong for this calibration. |
| UK-DALE decode timing and per-lot duration estimate | One `file_partials` run: 3.361 s for 197.106 MB (0.01705 s/MB). Linear decode-only estimates: cal_1 6.7 s, cal_2 10.3 s, cal_3 28.1 s; test_1 10.0 s, test_2 17.4 s, test_3 40.4 s. |
| Real pilot/grid/size-up/final campaigns | Not run; waiting for the user to launch sequential experiments after the budget gate. |
| Campaign budget-only estimates / 24-hour gate | Budget-only CLI paths verified without preparation or experiment launch: 75 pilot, 135 grid, and 150 conservative pre-fit final runs; timeout bounds total 360 h. No default real `runs.csv` exists, so these are not measured runtime estimates and do not trigger reductions. |
| MetroPT-3 incident dates/mining | Four intervals sourced from UCI Dataset 791 and marked verified. The cited 2022 paper's intervals concern a different dataset and were not applied. Mining ran; all four intervals are outside the current test split, so `incidents_evaluable` is 0 and no held-out detection claim is supported. |
| State of the art (>=8 non-paywalled references since 2023) | To do by the authors. |
| Report text and `contributions.md` | To do by the authors; `report/report.md` remains a skeleton. |
| Multi-node protocol | Documented, not executed. |

## Commands and checks run

- `make PY=./.venv/bin/python env` — passed; recorded Python 3.13.5, Java 25.0.4.1, PySpark 4.3.0, pandas 3.1.1, 4 physical cores, 15.5 GB RAM, and 303.3 GB free disk.
- `make PY=./.venv/bin/python test` — 31 passed in 17.53 s; two PySpark/pandas compatibility warnings.
- `make PY=./.venv/bin/python metropt` — manifest hashes, audit, and Parquet preparation completed. Audit: median time step 10 s; 331 gaps over 60 s; largest gap 172,918 s.
- `make PY=./.venv/bin/python ukdale-list WEEKS="2013/wk11"` — passed; browse page contained 49 FLAC links; 38 files were sized, totaling 7.080 GiB, enough to meet configured targets and realized-ratio constraints.
- `make PY=./.venv/bin/python lots` — passed; calibration lots were 0.366, 0.562, and 1.534 GiB; test lots were 0.547, 0.952, and 2.209 GiB. Both actual largest/smallest ratios are >=4. The largest lots exceed their nominal targets because FLAC files cannot be split.
- `make PY=./.venv/bin/python ukdale-debug WEEK="2013/wk11"` — HTTP 200, final browse URL and `text/html; charset=utf-8` printed.
- Downloaded `calibration_house_1.cfg` (125 bytes) and one FLAC (197,105,625 bytes); recorded the FLAC SHA-256 in `manifests/ukdale_all.csv`.
- `PYTHONPATH=src ./.venv/bin/python -m bigdata.ukdale verify data/raw/ukdale/house_1/2013/wk11/vi-1363392000_236972.flac --cal data/raw/ukdale/calibration_house_1.cfg` — passed mains-voltage channel check after setting `int_shift_bits: 0`. File duration 3599.573 s; next filename start is 3600.054 s later (0.481 s gap).
- `file_partials` decode timing — one measured run only; estimates above are linear source-byte projections, not Spark/campaign runtime estimates.
- `PYTHONPATH=src ./.venv/bin/python -m bigdata.campaign pilot --budget-only`, `grid --budget-only`, and `final --budget-only` — all exited without preparation or experiments. With no default run log, outputs were timeout-only bounds (75/135/150 runs; 360 h total); the pre-fit final plan was explicitly labeled an upper bound.
- `make PY=./.venv/bin/python mining` — completed. Validation false-alert rate was 0.375/day; test contained 0 evaluable verified incidents, so no test detection result is claimed.
- `./.venv/bin/python -m compileall -q src/bigdata tests scripts/select_grid_p.py` and `bash -n scripts/run_all.sh` — passed.
- Ruff/flake8 and PowerShell validation were unavailable (`ruff`, `flake8`, and `pwsh` not installed).
- `make PY=./.venv/bin/python smoke` — passed; campaign runs were skipped because existing smoke run IDs were already present. Synthetic results are not project findings.
- `make PY=./.venv/bin/python package` — passed; regenerated `dist/tests.zip` and `dist/results.zip` after the README and mining updates.
- `git diff --check` — passed; Git reported only a CRLF-to-LF normalization warning for `results/preparation_costs.csv`.
- The CEDA filename uses `vi-<epoch>_<microseconds>.flac`; acquisition and timestamp parsing now accept the hyphen and retain compatibility with the earlier form.

## Remaining manual steps

1. Run the first real pilot, then `python -m bigdata.campaign pilot --budget-only`, `grid --budget-only`, and `final --budget-only`; total the estimates. Apply the specified reductions in order only if the total exceeds 24 hours, recording each reduction here and in `ASSUMPTIONS.md`.
2. Launch `scripts/run_all.sh` or `scripts/run_all.ps1` only after the budget gate. Campaigns are sequential and resumable; do not run concurrent Spark jobs.
3. Write the state of the art, report narrative, and `contributions.md`; distinguish single-machine local parallelism from an unexecuted cluster protocol.
