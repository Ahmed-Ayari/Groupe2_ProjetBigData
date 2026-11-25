"""PySpark implementations. DataFrame/SQL for tabular ops; NumPy only for FLAC decoding on workers.

No collect()/toPandas() on data here. Outputs are written as Parquet (or the `noop` sink for
phase-isolation probes via stop_after).
"""
from __future__ import annotations
import os, sys
from pathlib import Path
from pyspark.sql import SparkSession, Window, functions as F

UK_SCHEMA = "window_id long, n long, sum_i2 double, sum_u2 double, sum_p double, max_i double"


def make_spark(cfg: dict, p: int, P: int, aqe: bool, event_dir: Path, app: str) -> SparkSession:
    sc = cfg["spark"]
    tmp = Path(sc["local_tmp"])
    tmp = tmp if tmp.is_absolute() else Path(__file__).resolve().parents[2] / tmp
    tmp.mkdir(parents=True, exist_ok=True)
    event_dir.mkdir(parents=True, exist_ok=True)
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    src = str(Path(__file__).resolve().parents[1])
    os.environ["PYTHONPATH"] = src + os.pathsep + os.environ.get("PYTHONPATH", "")
    b = (SparkSession.builder.master(f"local[{p}]").appName(app)
         .config("spark.driver.memory", sc["driver_memory"])
         .config("spark.sql.shuffle.partitions", str(P))
         .config("spark.sql.adaptive.enabled", str(bool(aqe)).lower())
         .config("spark.sql.session.timeZone", "UTC")
         .config("spark.dynamicAllocation.enabled", "false")
         .config("spark.eventLog.enabled", "true")
         .config("spark.eventLog.dir", event_dir.resolve().as_uri())
         .config("spark.eventLog.rolling.enabled", "false")
         .config("spark.eventLog.compress", "false")
         .config("spark.local.dir", str(tmp))
         .config("spark.ui.enabled", "false")
         .config("spark.sql.execution.arrow.pyspark.enabled", "true"))
    spark = b.getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def _sink(df, stop_after: str, out_path: str | None):
    if stop_after == "write":
        df.write.mode("errorifexists").parquet(out_path)
    else:                                  # decode/compute probes: force full evaluation, discard output
        df.write.format("noop").mode("overwrite").save()


# ------------------------------------------------------------------ MetroPT-3 ------------------
def metropt_a(spark, input_path: str, cols: list[str], w_s: int, equipment_id: str, scope: str):
    """5-minute windows: n, mean, max, std_pop per sensor. scope: prepared (parquet) | raw (csv)."""
    w_us = int(w_s * 1_000_000)
    if scope == "prepared":
        df = spark.read.parquet(input_path).select("ts_us", *cols)
    else:
        schema = "timestamp string, " + ", ".join(f"{c} double" for c in cols)
        raw = spark.read.csv(input_path, header=True, schema=schema)
        df = raw.select(F.expr("unix_micros(to_timestamp(timestamp))").alias("ts_us"), *cols)
    df = df.withColumn("window_id", F.expr(f"ts_us div {w_us}"))
    aggs = []
    for c in cols:
        aggs += [F.count(c).alias(f"{c}__n"), F.avg(c).alias(f"{c}__mean"),
                 F.max(c).alias(f"{c}__max"), F.stddev_pop(c).alias(f"{c}__std_pop")]
    out = df.groupBy("window_id").agg(*aggs)
    out = out.withColumn("equipment_id", F.lit(equipment_id)).withColumn("window_start_s", F.col("window_id") * F.lit(float(w_s)))
    order = ["equipment_id", "window_id", "window_start_s"] + [f"{c}__{s}" for c in cols for s in ("n", "mean", "max", "std_pop")]
    return out.select(*order)


# ------------------------------------------------------------------ UK-DALE --------------------
def ukdale_partials_raw(spark, files: list[str], cal: tuple[float, float], w_s: float, block_seconds: float,
                        channel_order: tuple[str, str], int_shift_bits, Q: int):
    """Distribute file PATHS (never samples); decode + calibrate + reduce on workers."""
    v_step, a_step = cal
    cfg_tuple = (float(w_s), float(block_seconds), tuple(channel_order), int_shift_bits)

    def fn(it):
        from bigdata.ukdale import Calibration, file_partials
        c = Calibration(v_step, a_step)
        for pdf in it:
            for path in pdf["path"]:
                yield file_partials(path, c, cfg_tuple[0], cfg_tuple[1], cfg_tuple[2], cfg_tuple[3])

    paths = spark.createDataFrame([(f,) for f in files], "path string").repartition(Q)
    return paths.mapInPandas(fn, UK_SCHEMA)


def ukdale_partials_prepared(spark, prepared_files: list[str]):
    return spark.read.parquet(*prepared_files)


def ukdale_merge(partials, w_s: float, equipment_id: str, strategy: str, P: int):
    """Shuffle step: merge per-(file,window) partial sums into per-window indicators."""
    if strategy == "range":
        partials = partials.repartitionByRange(P, "window_id")
    g = partials.groupBy("window_id").agg(
        F.sum("n").alias("n"), F.sum("sum_i2").alias("sum_i2"), F.sum("sum_u2").alias("sum_u2"),
        F.sum("sum_p").alias("sum_p"), F.max("max_i").alias("i_max"))
    return g.select(
        F.lit(equipment_id).alias("equipment_id"), "window_id",
        (F.col("window_id") * F.lit(float(w_s))).alias("window_start_s"), "n",
        F.sqrt(F.col("sum_i2") / F.col("n")).alias("i_rms"),
        F.sqrt(F.col("sum_u2") / F.col("n")).alias("v_rms"),
        (F.col("sum_p") / F.col("n")).alias("p_mean"), "i_max")


# ------------------------------------------------------------------ Treatment B ----------------
def treatment_b(df, feats: list[str], w_s: float, history_s: float, n_col):
    """Time-based delta and history features (same definition as windows.treatment_b).

    Note: partitioning by equipment_id puts one equipment in one task: this is the documented
    parallelism limit of Treatment B on a single equipment.
    """
    k = int(round(history_s / w_s))
    wo = Window.partitionBy("equipment_id").orderBy("window_id")
    wr = wo.rangeBetween(-k, -1)
    out = df.withColumn("_prev_id", F.lag("window_id").over(wo))
    contiguous = (F.col("window_id") - F.col("_prev_id")) == 1
    out = out.withColumn("prev_missing", (~F.coalesce(contiguous, F.lit(False))).cast("int"))
    for f in feats:
        nc = n_col[f] if isinstance(n_col, dict) else n_col
        out = out.withColumn(f"delta_{f}", F.when(F.col("prev_missing") == 0, F.col(f) - F.lag(f).over(wo)))
        out = out.withColumn(f"hist_{f}", F.sum(F.col(nc) * F.col(f)).over(wr) / F.sum(F.col(nc)).over(wr))
    return out.drop("_prev_id")
