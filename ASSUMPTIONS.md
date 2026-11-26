# Assumptions and known limits (read before trusting any number)

1. "Node" p = Spark cores in `local[p]`; machine = single PC. Cores per node = 1; driver memory is shared by all cores.
2. House 1 calibration was checked against `2013/wk11/vi-1363392000_236972.flac` (PCM_24, 16 kHz, 2 channels).
   The config's `volts_per_adc_step=1.90101491444e-07` and `amps_per_adc_step=4.9224284384e-08` keys match the parser.
   Channel 0 is voltage: its first-five-second RMS is 243.404 V with `int_shift_bits=0` (channel 1 is 6.737 V).
   `auto` selects an 8-bit shift for PCM_24 and yields only 0.951 V on channel 0, so it is incorrect for this calibration.
   The verified setting is `int_shift_bits: 0`; rerun
   `python -m bigdata.ukdale verify <file.flac> --cal data/raw/ukdale/calibration_house_1.cfg`
   if the source file, channel format, or calibration changes.
   Filename start is `1363392000.236972` epoch seconds; file duration is 3599.573 s and the next filename starts
   3600.054 s later, leaving a 0.481 s gap. Continue checking filename timing against decoded duration for other weeks.
3. Calibration cfg keys are read by name (`volts_per_adc_step`, `amps_per_adc_step`); the parser fails loudly if they differ.
4. Window convention: half-open [start, start+w); windows are keyed by integer `window_id`; population std (ddof=0).
5. MetroPT-3 duplicates: removed globally in the prepare step. Raw-CSV scope assumes the audit reports 0 duplicate rows.
6. Treatment B history is TIME-based (windows with id in [t-k, t-1]), n-weighted; a missing previous window gives NaN and `prev_missing=1`.
7. Spark `P_effective` = tasks of the last shuffle-reading stage (after AQE coalescing); estimate, not an API value.
8. Phase times (decode / shuffle / write) come from stop_after probes (noop sink) and differences of medians, not from a profiler.
9. OS file cache is NOT controlled (`cold_or_warm=os_cache_not_controlled`). Randomised run order reduces, but does not remove, this bias.
10. Treatment B runs partition by equipment: one equipment is processed by one task (documented parallelism limit).
11. Deadlines are derived from calibration throughput quantiles (configs/default.yaml `selector.deadline_scenarios`), defined before any test run.
12. Lots are built by walking the manifest in time order and interleaving calibration and test lots (disjoint files, one skipped file between lots). Because files are indivisible, the largest lot in each split is extended as needed to reach the configured 4:1 realized-byte ratio; actual lot sizes can exceed targets.
13. Node-minutes (core-minutes here) are NOT kWh or CO2.
14. MetroPT-3 incident intervals come from the UCI MetroPT-3 Dataset 791 "Failure Information" table, not from the 2022 MetroPT paper; the UCI table itself labels both the 2020-04-18 and 2020-05-29 reports "#1". Mining claims concern detection of ongoing incidents only, never prediction.
15. Mining uses expanding-window fits: scaler and IsolationForest are fit strictly before each incident, excluding verified incident intervals; a normal preceding-day slice sets the false-alert threshold and each test spans one day before through one day after the incident. The first incident (18 Apr) has comparatively little history for training.
16. UK-DALE directory listings use `data.ceda.ac.uk`; downloads and HEAD requests use `dap.ceda.ac.uk`. Listings and HEAD sizes are cached; when HTML has no file links, use a browser-copied URL list with `--filelist`.
