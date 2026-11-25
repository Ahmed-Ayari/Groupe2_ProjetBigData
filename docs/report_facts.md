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

## Median / min / max duration_s (s) per dataset, method, p, scope (filter: status=OK, stop_after=write)

| dataset | method | p | scope | lot | n | median | min | max |
|---|---|---|---|---|---|---|---|---|
| metropt | B0 | 1 | prepared | metropt3 | 3 | 85.39 | 83.29 | 89.38 |
| metropt | B0 | 1 | raw | metropt3 | 3 | 87.25 | 85.41 | 88.29 |
| metropt | PILOT | 1 | prepared | metropt3 | 3 | 8.18 | 7.96 | 8.33 |
| metropt | PILOT | 2 | prepared | metropt3 | 3 | 8.41 | 7.52 | 8.94 |
| metropt | PILOT | 4 | prepared | metropt3 | 3 | 8.98 | 8.16 | 9.21 |
| ukdale | B0 | 1 | prepared | cal_1 | 3 | 0.02 | 0.02 | 0.07 |
| ukdale | B0 | 1 | prepared | cal_2 | 3 | 0.04 | 0.04 | 0.05 |
| ukdale | B0 | 1 | raw | cal_1 | 3 | 6.06 | 5.94 | 6.48 |
| ukdale | B0 | 1 | raw | cal_2 | 3 | 9.69 | 8.82 | 10.61 |
| ukdale | B0 | 1 | raw | cal_3 | 3 | 25.69 | 25.69 | 26.03 |
| ukdale | B0 | 1 | raw | test_1 | 5 | 9.84 | 9.65 | 9.90 |
| ukdale | B0 | 1 | raw | test_2 | 5 | 15.99 | 15.89 | 16.24 |
| ukdale | B0 | 1 | raw | test_3 | 5 | 38.59 | 38.25 | 39.26 |
| ukdale | B1 | 1 | raw | cal_1 | 3 | 11.72 | 11.65 | 11.74 |
| ukdale | B1 | 1 | raw | cal_2 | 3 | 14.94 | 14.89 | 15.10 |
| ukdale | B1 | 1 | raw | cal_3 | 3 | 31.13 | 30.97 | 31.29 |
| ukdale | B1 | 1 | raw | test_1 | 5 | 15.29 | 14.91 | 15.62 |
| ukdale | B1 | 1 | raw | test_2 | 5 | 21.56 | 21.42 | 21.91 |
| ukdale | B1 | 1 | raw | test_3 | 5 | 44.23 | 43.53 | 45.08 |
| ukdale | B2 | 2 | raw | test_1 | 5 | 12.21 | 12.20 | 12.25 |
| ukdale | B2 | 2 | raw | test_2 | 5 | 16.38 | 16.22 | 16.73 |
| ukdale | B2 | 2 | raw | test_3 | 5 | 29.67 | 29.06 | 29.86 |
| ukdale | B2 | 4 | raw | test_1 | 5 | 10.16 | 10.02 | 10.61 |
| ukdale | B2 | 4 | raw | test_2 | 5 | 14.47 | 14.35 | 14.58 |
| ukdale | B2 | 4 | raw | test_3 | 5 | 23.68 | 23.39 | 24.04 |
| ukdale | B3 | 1 | raw | test_2 | 5 | 21.64 | 21.37 | 21.79 |
| ukdale | B3 | 1 | raw | test_3 | 10 | 44.01 | 43.76 | 44.28 |
| ukdale | B3 | 2 | raw | test_2 | 5 | 16.46 | 16.01 | 16.58 |
| ukdale | B3 | 4 | raw | test_1 | 5 | 10.20 | 10.09 | 10.34 |
| ukdale | B4 | 1 | raw | test_2 | 5 | 21.44 | 21.22 | 21.55 |
| ukdale | B4 | 1 | raw | test_3 | 10 | 43.92 | 43.52 | 44.48 |
| ukdale | B4 | 2 | raw | test_2 | 5 | 16.26 | 16.04 | 16.57 |
| ukdale | B4 | 4 | raw | test_1 | 5 | 10.17 | 10.14 | 10.32 |
| ukdale | B4_nomargin | 1 | raw | test_1 | 5 | 14.89 | 14.74 | 15.21 |
| ukdale | B4_nomargin | 1 | raw | test_2 | 10 | 21.36 | 21.19 | 21.59 |
| ukdale | B4_nomargin | 1 | raw | test_3 | 10 | 43.87 | 43.52 | 44.43 |
| ukdale | B4_nomargin | 4 | raw | test_1 | 5 | 10.10 | 9.79 | 10.50 |
| ukdale | GRID | 1 | prepared | cal_2 | 12 | 3.53 | 3.21 | 5.66 |
| ukdale | GRID | 1 | raw | cal_2 | 9 | 15.41 | 14.57 | 19.87 |
| ukdale | GRID | 2 | prepared | cal_2 | 12 | 3.42 | 3.23 | 4.87 |
| ukdale | GRID | 2 | raw | cal_2 | 9 | 12.30 | 11.30 | 16.24 |
| ukdale | GRID | 4 | prepared | cal_2 | 12 | 3.46 | 3.38 | 5.00 |
| ukdale | GRID | 4 | raw | cal_2 | 9 | 10.44 | 9.41 | 11.69 |
| ukdale | GRID_AQEOFF | 1 | prepared | cal_2 | 9 | 5.22 | 3.72 | 8.78 |
| ukdale | GRID_AQEOFF | 2 | prepared | cal_2 | 9 | 4.46 | 3.55 | 7.97 |
| ukdale | GRID_AQEOFF | 4 | prepared | cal_2 | 9 | 4.23 | 3.62 | 7.41 |
| ukdale | GRID_Q | 4 | raw | cal_2 | 12 | 10.64 | 10.17 | 14.99 |
| ukdale | GRID_STRAT | 1 | prepared | cal_2 | 9 | 5.15 | 3.95 | 9.45 |
| ukdale | GRID_STRAT | 2 | prepared | cal_2 | 9 | 4.52 | 3.35 | 7.22 |
| ukdale | GRID_STRAT | 4 | prepared | cal_2 | 9 | 4.30 | 3.53 | 6.39 |
| ukdale | PILOT | 1 | prepared | cal_1 | 3 | 2.95 | 2.93 | 3.00 |
| ukdale | PILOT | 1 | raw | cal_1 | 3 | 10.72 | 10.71 | 10.82 |
| ukdale | PILOT | 2 | prepared | cal_1 | 3 | 2.99 | 2.94 | 3.01 |
| ukdale | PILOT | 2 | raw | cal_1 | 3 | 10.48 | 10.42 | 10.56 |
| ukdale | PILOT | 4 | prepared | cal_1 | 3 | 2.97 | 2.95 | 3.00 |
| ukdale | PILOT | 4 | raw | cal_1 | 3 | 8.41 | 8.41 | 8.62 |
| ukdale | SIZEUP | 2 | raw | cal_1 | 3 | 11.57 | 11.43 | 11.59 |
| ukdale | SIZEUP | 2 | raw | cal_2 | 3 | 12.32 | 12.26 | 12.54 |
| ukdale | SIZEUP | 2 | raw | cal_3 | 3 | 21.41 | 21.20 | 21.43 |
| ukdale | SIZEUP | 2 | raw | test_1 | 3 | 12.50 | 12.26 | 12.57 |
| ukdale | SIZEUP | 2 | raw | test_2 | 3 | 16.67 | 16.49 | 16.70 |
| ukdale | SIZEUP | 2 | raw | test_3 | 3 | 29.27 | 29.13 | 29.67 |
| ukdale | SIZEUP | 4 | raw | cal_1 | 3 | 9.16 | 9.11 | 9.17 |
| ukdale | SIZEUP | 4 | raw | cal_2 | 3 | 10.22 | 9.97 | 10.30 |
| ukdale | SIZEUP | 4 | raw | cal_3 | 3 | 17.59 | 17.44 | 17.87 |
| ukdale | SIZEUP | 4 | raw | test_1 | 3 | 10.26 | 10.20 | 10.78 |
| ukdale | SIZEUP | 4 | raw | test_2 | 3 | 14.40 | 14.33 | 14.66 |
| ukdale | SIZEUP | 4 | raw | test_3 | 3 | 23.96 | 23.67 | 23.97 |

## results/decisions.json
```
{
  "model": "loglinear",
  "cv": {
    "rule_volume": {
      "mape": 0.2588360473759193,
      "mae_s": 3.808223445343833
    },
    "loglinear": {
      "mape": 0.0918062230193333,
      "mae_s": 1.3200485244425424
    },
    "tree_depth<=3": {
      "mape": 0.24112840279005446,
      "mae_s": 3.750460025844663
    }
  },
  "margin_s": 3.8793680173988707,
  "B2": {
    "p": 2,
    "P": 256
  },
  "n_calibration_runs": 63,
  "fit_and_select_seconds": 0.13361526500011678,
  "calibration_cost_s": 1250.2277054349906
}
```

## results/final_summary.csv
```
scenario,method,hit_rate,runs_or_decisions,infeasible,median_cost_core_min
moderate,B2,1.0,15,0,0.5460589124000156
moderate,B3,0.9090909090909091,11,1,0.6412561723499797
moderate,B4,0.9090909090909091,11,1,0.6370980750166685
moderate,B4_nomargin,1.0,15,0,0.673279334733282
tight,B2,1.0,15,0,0.9649786228001176
tight,B3,1.0,15,0,0.6797254841333294
tight,B4,1.0,15,0,0.6780557251334055
tight,B4_nomargin,1.0,15,0,0.3570838338666969

```

## results/final_paired.csv
```
scenario,comparison,mean_ratio,ci_low,ci_high,n_lots,ci_method
moderate,cost B4/B3 (paired by lot),0.9927875280829803,0.9877384371888194,0.9978366189771413,2,"percentile bootstrap over lots, 5000 resamples; wide with few lots; not a coverage guarantee"
tight,cost B4/B3 (paired by lot),0.995446999135759,0.990966790118453,0.9978307269263847,3,"percentile bootstrap over lots, 5000 resamples; wide with few lots; not a coverage guarantee"

```

## results/metropt_mining.json
```
{
  "threshold": 0.5741113225306826,
  "n_features": 76,
  "k_consecutive": 3,
  "validation_days": 42.041666666666664,
  "false_alerts_per_day": 0.3753359941353751,
  "incidents_evaluable": 0,
  "incidents_detected": 0,
  "median_detection_delay_min": null,
  "claim": "detection of an ongoing incident, not failure prediction"
}
```

## results/preparation_costs.csv
```
step,seconds,input_bytes,output_bytes,timestamp
metropt_csv_to_parquet,1.426,218300507,32065832,2026-11-25T10:08:29.013775+00:00
metropt_csv_to_parquet,1.554,218300507,32065832,2026-11-25T10:21:58.920681+00:00
metropt_csv_to_parquet,1.445,218300507,32065832,2026-11-25T14:06:31.120355+00:00
ukdale_prepare_cal_1,6.815,392575550,317002,2026-11-25T15:09:35.364916+00:00
ukdale_prepare_cal_2,9.002,603319607,478780,2026-11-25T15:45:45.489129+00:00
ukdale_prepare_cal_3,26.546,1646840722,1276906,2026-11-25T16:14:43.081636+00:00
ukdale_prepare_test_1,10.081,587125351,474294,2026-11-25T16:26:02.286724+00:00
ukdale_prepare_test_2,16.485,1022156739,800493,2026-11-25T16:26:18.772703+00:00
ukdale_prepare_test_3,39.583,2371685973,1911263,2026-11-25T16:26:58.357542+00:00

```