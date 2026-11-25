# Pilot diagnosis (generated from results/runs.csv, method=PILOT, UK-DALE, raw scope)

| lot | p | decode (s) | compute-decode (s) | write-compute (s) | total (s) | dominant phase |
|---|---|---|---|---|---|---|
| cal_1 | 1 | 9.45 | 0.93 | 0.35 | 10.72 | read+decode |
| cal_1 | 2 | 9.24 | 0.71 | 0.53 | 10.48 | read+decode |
| cal_1 | 4 | 7.10 | 0.89 | 0.42 | 8.41 | read+decode |

Interpretation (to be written by the author from the table above): if read+decode dominates, tuning P (shuffle partitions) can only have a small effect and the read partitioning Q becomes the relevant knob.