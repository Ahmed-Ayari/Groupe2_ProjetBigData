# STATUS (updated 2026-11-25; real results are never inferred from smoke data)

| Step | State |
|---|---|
| Code, configs, runner, selector, mining, plots, packaging | Written; `scripts/run_all.sh` added; PowerShell runner added but not executed (`pwsh` unavailable). |
| Acquisition parser/retry tests | 2 passed; HTML fixture and mocked HTTP 503→200 retry. |
| Full tests | 26 passed; 2 PySpark warnings that pandas >=3 is not fully supported. |
| Synthetic smoke pipeline | `make smoke` completed; existing smoke run IDs were all skipped, so no Spark experiments ran in this invocation. |
| MetroPT-3 | Download, audit, and Parquet preparation completed on 2026-11-25; 1,516,948 rows; 0 duplicate rows/timestamps; 0 duplicates removed. |
| UK-DALE listing/download/calibration verification | Blocked: CEDA browse request failed after transient 503s and TLS EOF. No UK-DALE file was downloaded or verified. |
| UK-DALE decode timing and per-lot duration estimate | Not run; requires verified FLAC input. |
| Real pilot/grid/size-up/final campaigns | Not run; blocked on UK-DALE acquisition and verification. |
| Campaign budget-only estimates / 24-hour gate | Not run; no real pilot history, lots, or final decisions exist. Lot targets were reduced as requested; repetition reductions are pending measured estimates. |
| MetroPT-3 incident dates | Four intervals sourced from UCI Dataset 791 and marked verified. The cited 2022 paper's intervals concern a different dataset and were not applied. Mining itself was not run. |
| State of the art (>=8 non-paywalled references since 2023) | To do by the authors. |
| Report text and `contributions.md` | To do by the authors; `report/report.md` remains a skeleton. |
| Multi-node protocol | Documented, not executed. |

## Commands and checks run

- `make PY=./.venv/bin/python env` — passed; recorded Python 3.13.5, Java 25.0.4.1, PySpark 4.3.0, pandas 3.1.1, 4 physical cores, 15.5 GB RAM, and 303.3 GB free disk.
- `make PY=./.venv/bin/python test` — 26 passed in 17.10 s; two PySpark/pandas compatibility warnings.
- `make PY=./.venv/bin/python metropt` — manifest hashes, audit, and Parquet preparation completed. Audit: median time step 10 s; 331 gaps over 60 s; largest gap 172,918 s.
- `PYTHONPATH=src ./.venv/bin/python -m bigdata.acquire ukdale-debug --week 2013/wk11` — failed before an HTTP response was available (TLS EOF; retries observed 503). The independent web fetch also could not connect to `data.ceda.ac.uk`.
- `./.venv/bin/python -m compileall -q src/bigdata tests scripts/select_grid_p.py` and `bash -n scripts/run_all.sh` — passed.
- Ruff/flake8 and PowerShell validation were unavailable (`ruff`, `flake8`, and `pwsh` not installed).
- `make PY=./.venv/bin/python smoke` — completed with synthetic data; all existing pilot/grid/size-up/final run IDs were skipped. Synthetic results are not project findings.
- Focused acquisition, incident, and P-selection tests passed; included in the full 26-test result above.

## Remaining manual steps

1. Retry `make ukdale-list WEEKS="2013/wk11"` once CEDA is reachable. If HTML contains no `.flac` links, inspect `ukdale-debug` output and provide a browser-copied URL list with `--filelist`.
2. Build the lots, download the calibration file and one actual FLAC first, inspect calibration keys and voltage RMS, and check filename-derived start time against decoded duration. Do not benchmark until these assumptions are verified.
3. Measure decode seconds/MB on that verified file; estimate lot durations from actual manifest bytes.
4. Run pilot and then the requested budget-only checks. Report their measured total; apply the documented reductions in order only if it exceeds 24 h, recording each reduction here and in `ASSUMPTIONS.md`.
5. Launch `scripts/run_all.sh` or `scripts/run_all.ps1` only after those checks. Campaigns are sequential and resumable; do not run concurrent Spark jobs.
6. Write the state of the art, report narrative, and `contributions.md`; distinguish single-machine local parallelism from an unexecuted cluster protocol.
