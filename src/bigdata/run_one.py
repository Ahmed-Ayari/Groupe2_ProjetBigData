"""Execute ONE experiment in a fresh process (fresh JVM). Writes a JSON result; the parent measures wall time/RSS."""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_v] = "1"          # one BLAS thread per task: no hidden oversubscription

import argparse, json, shutil, time
from pathlib import Path

from .config import load_config, resolve


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=["metropt", "ukdale"], required=True)
    ap.add_argument("--method", default="MANUAL")
    ap.add_argument("--engine", choices=["local", "spark"], required=True)
    ap.add_argument("--workload", choices=["A", "B"], default="A")
    ap.add_argument("--scope", choices=["raw", "prepared"], default="raw")
    ap.add_argument("--lot", default="metropt3")
    ap.add_argument("--p", type=int, default=1)
    ap.add_argument("--P", type=int, default=64)
    ap.add_argument("--Q", type=int, default=8)
    ap.add_argument("--aqe", type=int, default=1)
    ap.add_argument("--strategy", choices=["hash", "range"], default="hash")
    ap.add_argument("--stop-after", choices=["decode", "compute", "write"], default="write")
    ap.add_argument("--out", required=True)
    ap.add_argument("--event-dir", required=True)
    ap.add_argument("--result-json", required=True)
    a = ap.parse_args()

    cfg = load_config()
    raw, prep, man = resolve(cfg, "data_raw"), resolve(cfg, "data_prepared"), resolve(cfg, "manifests")
    w_m, w_u = cfg["windows"]["metropt_s"], cfg["windows"]["ukdale_s"]
    res: dict = {"rows_out": None}
    spark = None
    t_session = 0.0

    if a.engine == "spark":
        from .spark_jobs import make_spark
        t = time.perf_counter()
        spark = make_spark(cfg, a.p, a.P, bool(a.aqe), Path(a.event_dir), f"bd-{Path(a.out).name}")
        t_session = time.perf_counter() - t

    if a.dataset == "metropt":
        mm = json.loads((man / "metropt3.json").read_text())
        csv_p, pq_p = mm["csv_path"], mm["parquet_path"]
        from . import local_ref
        cols = local_ref.metropt_columns(pq_p if a.scope == "prepared" else csv_p, cfg["metropt"]["timestamp_col"])
        res["source_bytes"] = os.path.getsize(csv_p)
        res["prepared_bytes"] = os.path.getsize(pq_p) if a.scope == "prepared" else 0
        t0 = time.perf_counter()
        if a.engine == "local":
            src = pq_p if a.scope == "prepared" else csv_p
            df = local_ref.metropt_treatment_a(src, cfg)
            if a.workload == "B":
                df = local_ref.metropt_treatment_b(df, cfg)
            Path(a.out).mkdir(parents=True, exist_ok=True)
            df.to_parquet(Path(a.out) / "part-0.parquet", index=False)
            res["rows_out"] = len(df)
        else:
            from . import spark_jobs as S
            df = S.metropt_a(spark, pq_p if a.scope == "prepared" else csv_p, cols, w_m, cfg["metropt"]["equipment_id"], a.scope)
            if a.workload == "B":
                feats = [f"{c}__mean" for c in cols]
                df = S.treatment_b(df, feats, w_m, cfg["windows"]["history_s"], {f: f.replace("__mean", "__n") for f in feats})
            S._sink(df, a.stop_after, a.out)
        res["duration_s"] = time.perf_counter() - t0
    else:
        from .ukdale import parse_calibration
        from .prepare import prepared_paths
        lot_csv = man / "lots" / f"{a.lot}.csv"
        import pandas as pd
        lot = pd.read_csv(lot_csv)
        files = lot["local_path"].tolist()
        cal = parse_calibration(raw / "ukdale" / cfg["ukdale"]["calibration_file"])
        pfiles = prepared_paths(lot_csv, prep / "ukdale", w_u)
        res["source_bytes"] = int(lot["source_bytes"].sum())
        res["prepared_bytes"] = sum(os.path.getsize(f) for f in pfiles) if a.scope == "prepared" else 0
        u = cfg["ukdale"]
        t0 = time.perf_counter()
        if a.engine == "local":
            from . import local_ref, windows as W
            if a.scope == "raw":
                if a.method == "B0mp":
                    df = local_ref.ukdale_treatment_a_mp(files, cal, cfg, a.p)
                else:
                    df = local_ref.ukdale_treatment_a(files, cal, cfg)
            else:
                parts = pd.concat([pd.read_parquet(f) for f in pfiles], ignore_index=True)
                df = W.uk_finalize(W.uk_merge(parts), w_u, u["house"])
            if a.workload == "B":
                df = local_ref.ukdale_treatment_b(df, cfg)
            Path(a.out).mkdir(parents=True, exist_ok=True)
            df.to_parquet(Path(a.out) / "part-0.parquet", index=False)
            res["rows_out"] = len(df)
        else:
            from . import spark_jobs as S
            if a.scope == "raw":
                parts = S.ukdale_partials_raw(spark, files, (cal.volts_per_adc_step, cal.amps_per_adc_step), w_u,
                                              u["block_seconds"], tuple(u["channel_order"]), u["int_shift_bits"], a.Q)
            else:
                parts = S.ukdale_partials_prepared(spark, pfiles)
            if a.stop_after == "decode":
                S._sink(parts, "decode", None)
            else:
                df = S.ukdale_merge(parts, w_u, u["house"], a.strategy, a.P)
                if a.workload == "B":
                    df = S.treatment_b(df, ["i_rms", "p_mean"], w_u, cfg["windows"]["history_s"], "n")
                S._sink(df, a.stop_after, a.out)
        res["duration_s"] = time.perf_counter() - t0

    res["t_session_s"] = t_session
    if spark is not None:
        spark.stop()
    Path(a.result_json).write_text(json.dumps(res))


if __name__ == "__main__":
    main()
