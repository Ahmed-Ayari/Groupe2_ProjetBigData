# Project status

## Run 1 (archived)

The archived ledger contains 407 real campaign records dated 2026-11-25, all at code version `7f891df`. The table below is grouped directly from `results/archive_run1/runs.csv`.

| method | status | runs |
|---|---|---:|
| B0 | OK | 36 |
| B1 | OK | 24 |
| B2 | OK | 30 |
| B3 | OK | 25 |
| B4 | OK | 25 |
| B4_nomargin | OK | 30 |
| GRID | OK | 63 |
| GRID_AQEOFF | OK | 27 |
| GRID_Q | OK | 12 |
| GRID_STRAT | OK | 27 |
| PILOT | ERROR | 18 |
| PILOT | OK | 54 |
| SIZEUP | OK | 36 |

Status totals: ERROR=18, OK=389.

## Run 2 (current)

`results/runs.csv` currently contains 0 campaign records. No real run-2 campaign has been launched. Run-1 data and derived outputs remain under `results/archive_run1/`; run IDs include the code version, so the ledgers are not mixed.

## Completed code and validation

- Vectorized MetroPT B0 window partials; retained the exact merge path and tested numeric equivalence and Spark equivalence.
- Spark MetroPT raw ingestion selects timestamp/sensor columns by name, including CSVs with a leading index column.
- Added UK-DALE multiprocessing B0mp to size-up and final campaign specifications; it merges compact per-file partials using the existing reducer.
- Fixed infeasible-decision miss counts, per-run hit-rate reporting, multiplicative margin, deadline scenarios, paired statistics, and second-lot calibration-grid coverage.
- Updated the incident mining evaluation and verified incident source rows against the UCI dataset page.
- Full pytest suite passed (39 tests); `make smoke` passed on synthetic data and wrote only to its isolated smoke results directory.
- MetroPT expanding-window analysis evaluated 4 incidents; 3 were detected. This is ongoing-incident detection, never prediction; the first (18 Apr) incident has little training history.
- The optional larger-volume expansion was not retained: the week-12/13 download was too slow to complete within the available time. The verified original six-lot configuration is restored; its files remain disjoint between calibration and test.

## Remaining work

- Obtain/verify the source files required by the active lots (`make download`) before starting campaigns.
- Run the budget gate, then launch the sequential, resumable run-2 campaign with `bash scripts/run_all.sh`; do not run it concurrently with other Spark work.
- After run 2, regenerate diagnosis, report facts, figures, and package outputs from the completed ledger.
- Authors: write a state-of-the-art section with at least eight non-paywalled references published since 2023, complete the report narrative, and add `contributions.md`.
- The multi-node protocol is documented but has not been executed.
