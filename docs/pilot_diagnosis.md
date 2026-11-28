# Pilot diagnosis (generated from results/runs.csv, method=PILOT, UK-DALE, raw scope)

| lot | p | decode (s) | compute-decode (s) | write-compute (s) | total (s) | dominant phase |
|---|---|---|---|---|---|---|
| cal_1 | 1 | 10.06 | 0.80 | 0.55 | 11.42 | read+decode |
| cal_1 | 2 | 9.80 | 0.75 | 0.45 | 11.00 | read+decode |
| cal_1 | 4 | 7.72 | 0.62 | 0.49 | 8.83 | read+decode |

Interpretation (to be written by the author from the table above): if read+decode dominates, tuning P (shuffle partitions) can only have a small effect and the read partitioning Q becomes the relevant knob.