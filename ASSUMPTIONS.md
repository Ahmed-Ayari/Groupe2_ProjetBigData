# Assumptions and known limits (read before trusting any number)

1. "Node" p = Spark cores in `local[p]`; machine = single PC. Cores per node = 1; driver memory is shared by all cores.
2. UK-DALE FLAC channel order (voltage, current), int scaling (24-bit read as int32 is left-justified, shift 8 bits) and
   file start time from the filename are CONFIGURABLE ASSUMPTIONS with a verification command:
   `python -m bigdata.ukdale verify <file.flac> --cal data/raw/ukdale/calibration_house_1.cfg`.
   The calibrated voltage RMS must be near mains (about 230 V). Do not run the campaign before this check passes.
3. Calibration cfg keys are read by name (`volts_per_adc_step`, `amps_per_adc_step`); the parser fails loudly if they differ.
4. Window convention: half-open [start, start+w); windows are keyed by integer `window_id`; population std (ddof=0).
5. MetroPT-3 duplicates: removed globally in the prepare step. Raw-CSV scope assumes the audit reports 0 duplicate rows.
6. Treatment B history is TIME-based (windows with id in [t-k, t-1]), n-weighted; a missing previous window gives NaN and `prev_missing=1`.
7. Spark `P_effective` = tasks of the last shuffle-reading stage (after AQE coalescing); estimate, not an API value.
8. Phase times (decode / shuffle / write) come from stop_after probes (noop sink) and differences of medians, not from a profiler.
9. OS file cache is NOT controlled (`cold_or_warm=os_cache_not_controlled`). Randomised run order reduces, but does not remove, this bias.
10. Treatment B runs partition by equipment: one equipment is processed by one task (documented parallelism limit).
11. Deadlines are derived from calibration throughput quantiles (configs/default.yaml `selector.deadline_scenarios`), defined before any test run.
12. Lots are built by walking the manifest in time order and interleaving calibration and test lots (disjoint files, one skipped file between lots).
13. Node-minutes (core-minutes here) are NOT kWh or CO2.
14. MetroPT-3 incident intervals come from the UCI MetroPT-3 Dataset 791 "Failure Information" table, not from the 2022 MetroPT paper; the paper's incidents concern a different 2022 dataset and do not overlap this 2020 data.
15. Mining split boundaries (2020-06-07 21:36 and 2020-07-20 12:48) approximate the audited coverage's exact 60% and 80% time points (2020-02-01 through 2020-09-01) while keeping all four published intervals whole: three in train and the 2020-07-15 interval in validation.
16. UK-DALE directory listings use `data.ceda.ac.uk`; downloads and HEAD requests use `dap.ceda.ac.uk`. Listings and HEAD sizes are cached; when HTML has no file links, use a browser-copied URL list with `--filelist`.
