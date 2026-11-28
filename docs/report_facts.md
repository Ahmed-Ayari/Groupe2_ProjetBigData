# Report facts (auto-generated; every number comes from the listed file)

## Hardware (environment/hardware.json)
```
{
  "cpu_logical": 8,
  "cpu_physical": 4,
  "ram_gb": 15.5,
  "disk_free_gb": 303.3,
  "os": "Linux-6.12.118+deb13-amd64-x86_64-with-glibc2.41",
  "python": "3.13.5",
  "java": "java version \"25.0.4.1\" 2026-08-18 LTS",
  "pyspark": "4.3.0",
  "numpy": "2.5.5",
  "pandas": "3.1.1",
  "environment_id": "4c-15.5g-spark4.3.0"
}
```

## Runs by method and status (results/runs.csv, group by method,status)

| method | status | n |
|---|---|---|
| B0 | OK | 39 |
| B0mp | OK | 48 |
| B1 | OK | 24 |
| B2 | OK | 45 |
| B3 | OK | 40 |
| B4 | OK | 40 |
| B4_nomargin | OK | 40 |
| GRID | OK | 126 |
| GRID_AQEOFF | OK | 54 |
| GRID_Q | OK | 24 |
| GRID_STRAT | OK | 54 |
| PILOT | OK | 63 |
| SIZEUP | EQUIV_FAIL | 1 |
| SIZEUP | OK | 35 |

## Median / min / max duration_s (s) per dataset, method, p, scope (filter: status=OK, stop_after=write)

| dataset | method | p | scope | lot | n | median | min | max |
|---|---|---|---|---|---|---|---|---|
| metropt | B0 | 1 | prepared | metropt3 | 3 | 1.12 | 1.10 | 2.53 |
| metropt | B0 | 1 | raw | metropt3 | 3 | 1.90 | 1.87 | 3.21 |
| metropt | PILOT | 1 | prepared | metropt3 | 3 | 8.50 | 8.36 | 8.75 |
| metropt | PILOT | 1 | raw | metropt3 | 3 | 13.46 | 13.28 | 13.67 |
| metropt | PILOT | 2 | prepared | metropt3 | 3 | 8.45 | 7.81 | 8.65 |
| metropt | PILOT | 2 | raw | metropt3 | 3 | 9.54 | 9.50 | 9.84 |
| metropt | PILOT | 4 | prepared | metropt3 | 3 | 8.53 | 8.03 | 8.68 |
| metropt | PILOT | 4 | raw | metropt3 | 3 | 8.33 | 8.33 | 8.34 |
| ukdale | B0 | 1 | prepared | cal_1 | 6 | 0.04 | 0.03 | 0.05 |
| ukdale | B0 | 1 | prepared | cal_2 | 3 | 0.04 | 0.04 | 0.05 |
| ukdale | B0 | 1 | raw | cal_1 | 3 | 6.31 | 6.28 | 7.89 |
| ukdale | B0 | 1 | raw | cal_2 | 3 | 9.40 | 8.93 | 9.46 |
| ukdale | B0 | 1 | raw | cal_3 | 3 | 25.19 | 25.05 | 25.53 |
| ukdale | B0 | 1 | raw | test_1 | 5 | 9.12 | 8.96 | 9.77 |
| ukdale | B0 | 1 | raw | test_2 | 5 | 15.72 | 15.47 | 16.01 |
| ukdale | B0 | 1 | raw | test_3 | 5 | 38.20 | 37.42 | 39.12 |
| ukdale | B0mp | 2 | raw | cal_1 | 3 | 4.20 | 4.17 | 4.32 |
| ukdale | B0mp | 2 | raw | cal_2 | 3 | 7.41 | 7.38 | 7.48 |
| ukdale | B0mp | 2 | raw | cal_3 | 3 | 16.07 | 15.85 | 16.21 |
| ukdale | B0mp | 2 | raw | test_1 | 5 | 7.40 | 7.35 | 7.61 |
| ukdale | B0mp | 2 | raw | test_2 | 5 | 11.23 | 11.15 | 11.52 |
| ukdale | B0mp | 2 | raw | test_3 | 5 | 24.05 | 23.80 | 24.36 |
| ukdale | B0mp | 4 | raw | cal_1 | 3 | 4.31 | 4.10 | 4.37 |
| ukdale | B0mp | 4 | raw | cal_2 | 3 | 5.36 | 5.09 | 5.38 |
| ukdale | B0mp | 4 | raw | cal_3 | 3 | 12.28 | 11.97 | 12.37 |
| ukdale | B0mp | 4 | raw | test_1 | 5 | 5.36 | 5.33 | 5.43 |
| ukdale | B0mp | 4 | raw | test_2 | 5 | 9.37 | 9.23 | 9.49 |
| ukdale | B0mp | 4 | raw | test_3 | 5 | 18.25 | 17.78 | 18.44 |
| ukdale | B1 | 1 | raw | cal_1 | 3 | 11.59 | 11.48 | 11.61 |
| ukdale | B1 | 1 | raw | cal_2 | 3 | 14.65 | 14.42 | 14.68 |
| ukdale | B1 | 1 | raw | cal_3 | 3 | 30.25 | 30.19 | 30.45 |
| ukdale | B1 | 1 | raw | test_1 | 5 | 14.63 | 14.60 | 14.86 |
| ukdale | B1 | 1 | raw | test_2 | 5 | 20.84 | 20.70 | 21.36 |
| ukdale | B1 | 1 | raw | test_3 | 5 | 43.22 | 42.69 | 44.28 |
| ukdale | B2 | 2 | raw | test_1 | 5 | 12.02 | 11.88 | 12.11 |
| ukdale | B2 | 2 | raw | test_2 | 5 | 15.93 | 15.68 | 16.04 |
| ukdale | B2 | 2 | raw | test_3 | 5 | 29.01 | 28.36 | 29.55 |
| ukdale | B2 | 4 | raw | test_1 | 10 | 9.93 | 9.81 | 10.05 |
| ukdale | B2 | 4 | raw | test_2 | 10 | 14.06 | 13.88 | 14.24 |
| ukdale | B2 | 4 | raw | test_3 | 10 | 23.05 | 22.69 | 23.49 |
| ukdale | B3 | 1 | raw | test_2 | 5 | 20.85 | 20.72 | 21.11 |
| ukdale | B3 | 1 | raw | test_3 | 15 | 43.14 | 42.63 | 43.42 |
| ukdale | B3 | 2 | raw | test_1 | 5 | 11.93 | 11.89 | 11.98 |
| ukdale | B3 | 2 | raw | test_2 | 5 | 15.87 | 15.79 | 15.93 |
| ukdale | B3 | 4 | raw | test_1 | 5 | 9.80 | 9.60 | 10.05 |
| ukdale | B3 | 4 | raw | test_2 | 5 | 14.13 | 13.96 | 14.21 |
| ukdale | B4 | 1 | raw | test_2 | 10 | 20.86 | 20.70 | 20.97 |
| ukdale | B4 | 1 | raw | test_3 | 15 | 42.96 | 42.65 | 44.12 |
| ukdale | B4 | 2 | raw | test_1 | 5 | 12.02 | 11.81 | 12.15 |
| ukdale | B4 | 4 | raw | test_1 | 5 | 10.03 | 9.95 | 10.11 |
| ukdale | B4 | 4 | raw | test_2 | 5 | 14.05 | 13.99 | 14.20 |
| ukdale | B4_nomargin | 1 | raw | test_1 | 5 | 14.42 | 14.33 | 14.67 |
| ukdale | B4_nomargin | 1 | raw | test_2 | 10 | 20.83 | 20.68 | 20.98 |
| ukdale | B4_nomargin | 1 | raw | test_3 | 15 | 42.99 | 42.63 | 43.40 |
| ukdale | B4_nomargin | 2 | raw | test_1 | 5 | 11.90 | 11.86 | 12.12 |
| ukdale | B4_nomargin | 2 | raw | test_2 | 5 | 16.01 | 15.84 | 16.13 |
| ukdale | GRID | 1 | prepared | cal_1 | 12 | 3.16 | 3.12 | 4.35 |
| ukdale | GRID | 1 | prepared | cal_2 | 12 | 3.22 | 3.10 | 4.55 |
| ukdale | GRID | 1 | raw | cal_1 | 9 | 11.45 | 11.33 | 11.62 |
| ukdale | GRID | 1 | raw | cal_2 | 9 | 14.58 | 14.42 | 14.69 |
| ukdale | GRID | 2 | prepared | cal_1 | 12 | 3.21 | 3.17 | 4.53 |
| ukdale | GRID | 2 | prepared | cal_2 | 12 | 3.25 | 3.17 | 5.16 |
| ukdale | GRID | 2 | raw | cal_1 | 9 | 11.04 | 10.99 | 11.17 |
| ukdale | GRID | 2 | raw | cal_2 | 9 | 11.89 | 11.82 | 12.14 |
| ukdale | GRID | 4 | prepared | cal_1 | 12 | 3.20 | 3.12 | 4.43 |
| ukdale | GRID | 4 | prepared | cal_2 | 12 | 3.25 | 3.16 | 4.58 |
| ukdale | GRID | 4 | raw | cal_1 | 9 | 8.88 | 8.79 | 9.04 |
| ukdale | GRID | 4 | raw | cal_2 | 9 | 9.87 | 9.70 | 10.62 |
| ukdale | GRID_AQEOFF | 1 | prepared | cal_1 | 9 | 4.64 | 3.52 | 8.12 |
| ukdale | GRID_AQEOFF | 1 | prepared | cal_2 | 9 | 4.64 | 3.56 | 8.26 |
| ukdale | GRID_AQEOFF | 2 | prepared | cal_1 | 9 | 4.17 | 3.35 | 6.52 |
| ukdale | GRID_AQEOFF | 2 | prepared | cal_2 | 9 | 4.24 | 3.27 | 6.67 |
| ukdale | GRID_AQEOFF | 4 | prepared | cal_1 | 9 | 3.95 | 3.30 | 5.82 |
| ukdale | GRID_AQEOFF | 4 | prepared | cal_2 | 9 | 4.10 | 3.35 | 5.99 |
| ukdale | GRID_Q | 4 | raw | cal_1 | 12 | 9.27 | 8.72 | 10.71 |
| ukdale | GRID_Q | 4 | raw | cal_2 | 12 | 10.25 | 9.67 | 14.14 |
| ukdale | GRID_STRAT | 1 | prepared | cal_1 | 9 | 4.84 | 3.66 | 8.41 |
| ukdale | GRID_STRAT | 1 | prepared | cal_2 | 9 | 5.00 | 3.67 | 8.37 |
| ukdale | GRID_STRAT | 2 | prepared | cal_1 | 9 | 4.34 | 3.52 | 6.61 |
| ukdale | GRID_STRAT | 2 | prepared | cal_2 | 9 | 4.32 | 3.49 | 6.71 |
| ukdale | GRID_STRAT | 4 | prepared | cal_1 | 9 | 4.06 | 3.45 | 6.22 |
| ukdale | GRID_STRAT | 4 | prepared | cal_2 | 9 | 4.16 | 3.42 | 6.03 |
| ukdale | PILOT | 1 | prepared | cal_1 | 3 | 3.07 | 3.06 | 3.11 |
| ukdale | PILOT | 1 | raw | cal_1 | 3 | 11.42 | 11.38 | 11.56 |
| ukdale | PILOT | 2 | prepared | cal_1 | 3 | 3.11 | 3.10 | 3.16 |
| ukdale | PILOT | 2 | raw | cal_1 | 3 | 11.00 | 10.99 | 11.02 |
| ukdale | PILOT | 4 | prepared | cal_1 | 3 | 3.17 | 3.08 | 3.22 |
| ukdale | PILOT | 4 | raw | cal_1 | 3 | 8.83 | 8.80 | 8.99 |
| ukdale | SIZEUP | 2 | raw | cal_1 | 3 | 11.04 | 11.03 | 11.30 |
| ukdale | SIZEUP | 2 | raw | cal_2 | 3 | 11.88 | 11.85 | 11.93 |
| ukdale | SIZEUP | 2 | raw | cal_3 | 3 | 20.67 | 20.36 | 20.71 |
| ukdale | SIZEUP | 2 | raw | test_1 | 3 | 11.96 | 11.74 | 12.07 |
| ukdale | SIZEUP | 2 | raw | test_2 | 2 | 16.09 | 15.97 | 16.21 |
| ukdale | SIZEUP | 2 | raw | test_3 | 3 | 28.85 | 28.79 | 29.02 |
| ukdale | SIZEUP | 4 | raw | cal_1 | 3 | 8.82 | 8.69 | 9.00 |
| ukdale | SIZEUP | 4 | raw | cal_2 | 3 | 9.90 | 9.69 | 10.05 |
| ukdale | SIZEUP | 4 | raw | cal_3 | 3 | 17.19 | 17.06 | 17.30 |
| ukdale | SIZEUP | 4 | raw | test_1 | 3 | 10.10 | 9.75 | 10.16 |
| ukdale | SIZEUP | 4 | raw | test_2 | 3 | 14.25 | 14.04 | 14.29 |
| ukdale | SIZEUP | 4 | raw | test_3 | 3 | 23.14 | 23.03 | 23.17 |

## results/decisions.json
```
{
  "model": "loglinear",
  "cv": {
    "rule_volume": {
      "mape": 0.35653498562377506,
      "mae_s": 4.942440096484153
    },
    "loglinear": {
      "mape": 0.11234435505152018,
      "mae_s": 1.5194176292144468
    },
    "tree_depth<=3": {
      "mape": 0.1761155501858359,
      "mae_s": 2.5677340418050183
    }
  },
  "margin_relative": 0.20113047791727567,
  "margin_quantile": 0.9,
  "B2": {
    "p": 4,
    "P": 64
  },
  "n_calibration_runs": 90,
  "fit_and_select_seconds": 0.16562906699982705,
  "calibration_cost_s": 1663.5990930770058
}
```

## results/final_summary.csv
```
scenario,method,hit_rate,runs_or_decisions,infeasible_decisions,median_cost_core_min
moderate,B2,1.0,15,0,0.9377978436668248
moderate,B3,1.0,15,0,0.6534063593998629
moderate,B4,1.0,15,0,0.6685700441342003
moderate,B4_nomargin,1.0,15,0,0.396697634299926
strict,B2,0.8666666666666667,15,0,0.93717666019996
strict,B3,0.3333333333333333,15,1,0.8310866314418187
strict,B4,0.3333333333333333,15,1,0.8263948523666234
strict,B4_nomargin,0.3333333333333333,15,1,0.6237169951915955
tight,B2,1.0,15,0,0.5308783063332764
tight,B3,1.0,15,0,0.39766047696660584
tight,B4,1.0,15,0,0.4005390002334025
tight,B4_nomargin,1.0,15,0,0.3453522531000393

```

## results/final_paired.csv
```
scenario,lot,comparison,mean_ratio,ratio_min,ratio_max,run_to_run_dispersion,n_pairs,n_lots,ci_low,ci_high,ci_method,interpretation,note
moderate,test_1,cost B4/B3 by repetition,1.0235597745890535,1.0060739814008914,1.0448556287077346,0.017421491434868267,5,1,,,not applicable to a single lot,difference exceeds observed run-to-run dispersion,
moderate,test_2,cost B4/B3 by repetition,0.6565892446493985,0.6496316310602827,0.6625853168969783,0.005294944346787276,5,1,,,not applicable to a single lot,difference exceeds observed run-to-run dispersion,
moderate,test_3,cost B4/B3 by repetition,1.002006698005468,0.9907510929412641,1.024717649505454,0.012369047151894672,5,1,,,not applicable to a single lot,no measurable difference,
moderate,ALL,cost B4/B3 (per-lot paired means),0.8940519057479733,0.6565892446493985,1.0235597745890535,,15,3,,,not reported: fewer than 5 test lots,not assessed in aggregate,Fewer than 5 independent test lots: a bootstrap confidence interval would be unreliable.
tight,test_1,cost B4/B3 by repetition,1.0070505654661779,0.992906540975611,1.0182138464493786,0.011408680407053064,5,1,,,not applicable to a single lot,no measurable difference,
tight,test_2,cost B4/B3 by repetition,1.000254452245946,0.9877174708406682,1.0089171008862272,0.006979022767526668,5,1,,,not applicable to a single lot,no measurable difference,
tight,test_3,cost B4/B3 by repetition,0.9990013916964842,0.9873455597753725,1.0074606984834056,0.005726563451376938,5,1,,,not applicable to a single lot,no measurable difference,
tight,ALL,cost B4/B3 (per-lot paired means),1.002102136469536,0.9990013916964842,1.0070505654661779,,15,3,,,not reported: fewer than 5 test lots,not assessed in aggregate,Fewer than 5 independent test lots: a bootstrap confidence interval would be unreliable.
strict,test_2,cost B4/B3 by repetition,0.999761585655501,0.9897768558613189,1.004759184628336,0.008058245620065437,5,1,,,not applicable to a single lot,no measurable difference,
strict,test_3,cost B4/B3 by repetition,0.9957109261325401,0.9906330875056623,1.003399754617342,0.005419966868857173,5,1,,,not applicable to a single lot,no measurable difference,
strict,ALL,cost B4/B3 (per-lot paired means),0.9977362558940206,0.9957109261325401,0.999761585655501,,10,2,,,not reported: fewer than 5 test lots,not assessed in aggregate,Fewer than 5 independent test lots: a bootstrap confidence interval would be unreliable.

```

## results/metropt_mining.json
```
{
  "n_features": 76,
  "k_consecutive": 3,
  "evaluation": "expanding-window ongoing-incident detection; not failure prediction",
  "incidents_evaluable": 4,
  "incidents_detected": 3,
  "detection_rate": 0.75,
  "median_detection_delay_min": 10.0,
  "false_alerts_per_day_outside_incidents": 0.518872173678047,
  "incidents": [
    {
      "incident": 1,
      "start": "2020-04-18T00:00:00",
      "end": "2020-04-18T23:59:00",
      "detected": true,
      "detection_delay_min": 30.0,
      "false_alerts_outside_incident": 2,
      "false_alerts_per_day_outside_incident": 1.0013908205841446,
      "validation_false_alerts_per_day": 0.0,
      "validation_false_alert_budget_per_day": 1.0,
      "threshold": 0.5746103377173966,
      "training_windows": 18483,
      "validation_windows": 242,
      "test_windows": 814
    },
    {
      "incident": 2,
      "start": "2020-05-29T23:30:00",
      "end": "2020-05-30T06:00:00",
      "detected": false,
      "detection_delay_min": null,
      "false_alerts_outside_incident": 0,
      "false_alerts_per_day_outside_incident": 0.0,
      "validation_false_alerts_per_day": 0.0,
      "validation_false_alert_budget_per_day": 1.0,
      "threshold": 0.5941330170481258,
      "training_windows": 27575,
      "validation_windows": 250,
      "test_windows": 572
    },
    {
      "incident": 3,
      "start": "2020-06-05T10:00:00",
      "end": "2020-06-07T14:30:00",
      "detected": true,
      "detection_delay_min": 0.0,
      "false_alerts_outside_incident": 1,
      "false_alerts_per_day_outside_incident": 0.5,
      "validation_false_alerts_per_day": 0.0,
      "validation_false_alert_budget_per_day": 1.0,
      "threshold": 0.47439708038718337,
      "training_windows": 29121,
      "validation_windows": 288,
      "test_windows": 890
    },
    {
      "incident": 4,
      "start": "2020-07-15T14:30:00",
      "end": "2020-07-15T19:00:00",
      "detected": true,
      "detection_delay_min": 10.0,
      "false_alerts_outside_incident": 1,
      "false_alerts_per_day_outside_incident": 0.5841784989858012,
      "validation_false_alerts_per_day": 0.0,
      "validation_false_alert_budget_per_day": 1.0,
      "threshold": 0.5806524570836492,
      "training_windows": 38107,
      "validation_windows": 205,
      "test_windows": 547
    }
  ],
  "note": "The first incident (18 Apr) has comparatively little history for training.",
  "claim": "detection of an ongoing incident only, never prediction"
}
```

## results/preparation_costs.csv
not executed / not available