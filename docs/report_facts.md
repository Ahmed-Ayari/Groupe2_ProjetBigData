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

## Median / min / max duration_s (s) per dataset, method, p, scope (filter: status=OK, stop_after=write)

| dataset | method | p | scope | lot | n | median | min | max |
|---|---|---|---|---|---|---|---|---|

## results/decisions.json
not executed / not available

## results/final_summary.csv
not executed / not available

## results/final_paired.csv
not executed / not available

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