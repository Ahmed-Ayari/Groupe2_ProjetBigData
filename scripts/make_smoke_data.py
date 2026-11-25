"""Create a tiny SYNTHETIC dataset + manifests under smoke/ to exercise the whole pipeline in minutes.
Usage: BIGDATA_CONFIG=configs/smoke.yaml python scripts/make_smoke_data.py
Smoke results are NOT results of the project."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pandas as pd
from bigdata import synth
from bigdata.config import load_config, resolve
from bigdata.prepare import prepare_metropt

cfg = load_config()
raw, prep, man = resolve(cfg, "data_raw"), resolve(cfg, "data_prepared"), resolve(cfg, "manifests")
(man / "lots").mkdir(parents=True, exist_ok=True)
uk = raw / "ukdale"; uk.mkdir(parents=True, exist_ok=True)
synth.write_calibration(uk / cfg["ukdale"]["calibration_file"])
synth.make_metropt_csv(raw / "metropt" / "m.csv", hours=6)
print(prepare_metropt(raw / "metropt" / "m.csv", prep / "metropt.parquet", cfg))
(man / "metropt3.json").write_text(json.dumps({"csv_path": str(raw / "metropt" / "m.csv"), "parquet_path": str(prep / "metropt.parquet")}))
t0, splits, k = 1363546800, {}, 0
for lot, nfiles, sp in (("cal_1", 2, "calibration"), ("test_1", 3, "test"), ("cal_2", 4, "calibration"),
                        ("test_2", 6, "test"), ("cal_3", 8, "calibration"), ("test_3", 12, "test")):
    rows = []
    for i in range(nfiles):
        f = synth.write_flac(uk / lot, t0, 0, seconds=20, seed=k); t0 += 40; k += 1
        rows.append({"local_path": str(f), "source_bytes": f.stat().st_size, "start": t0, "split": sp, "lot_id": lot})
    pd.DataFrame(rows).to_csv(man / "lots" / f"{lot}.csv", index=False)
    splits[lot] = {"split": sp, "files": nfiles, "source_gb": sum(r["source_bytes"] for r in rows) / 2**30}
(man / "splits.json").write_text(json.dumps(splits, indent=2))
print("smoke data ready")
