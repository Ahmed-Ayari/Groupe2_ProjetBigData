"""PySpark vs B0 equivalence on SYNTHETIC extracts (includes file-boundary windows, gaps, Treatment B)."""
import json
import numpy as np
import pandas as pd
import pytest
from bigdata import synth, local_ref, ukdale, spark_jobs as S
from bigdata.equivalence import compare, read_parquet_dir
from bigdata.config import tol

pytest.importorskip("pyspark")


@pytest.fixture(scope="module")
def spark(tmp_path_factory, cfg):
    s = S.make_spark(cfg, 2, 8, True, tmp_path_factory.mktemp("ev"), "pytest")
    yield s
    s.stop()


def _write(df, path, spark_df=True):
    df.write.mode("overwrite").parquet(str(path))
    return read_parquet_dir(path)


def test_metropt_a_and_b(spark, tmp_path, cfg):
    from bigdata.prepare import prepare_metropt
    csv = synth.make_metropt_csv(tmp_path / "m.csv", hours=5, step_s=10)
    pq = tmp_path / "m.parquet"
    prepare_metropt(csv, pq, cfg)
    ref_a = local_ref.metropt_treatment_a(pq, cfg)
    cols = local_ref.metropt_columns(pq, "timestamp")
    sa = S.metropt_a(spark, str(pq), cols, 300, "metro1", "prepared")
    got = _write(sa, tmp_path / "a")
    a, r = tol(cfg)
    assert compare(got, ref_a, a, r)["ok"]
    # A leading unnamed index column must not shift the timestamp/sensor fields.
    indexed_csv = tmp_path / "m_with_index.csv"
    raw = pd.read_csv(csv)
    raw.insert(0, "Unnamed: 0", np.arange(len(raw)))
    raw.to_csv(indexed_csv, index=False)
    got_raw = _write(S.metropt_a(spark, str(indexed_csv), cols, 300, "metro1", "raw"), tmp_path / "araw")
    assert compare(got_raw, ref_a, a, r)["ok"]
    # Treatment B (the synthetic file has a gap, so NaN rules are exercised)
    ref_b = local_ref.metropt_treatment_b(ref_a, cfg)
    feats = [f"{c}__mean" for c in cols]
    sb = S.treatment_b(sa, feats, 300, 300, {f: f.replace("__mean", "__n") for f in feats})
    cmp = compare(_write(sb, tmp_path / "b"), ref_b, a, r)
    assert cmp["ok"], cmp
    assert ref_b.prev_missing.sum() >= 2                                      # gap detected, not silently bridged


def test_ukdale_raw_prepared_and_boundary(spark, tmp_path, cfg):
    synth.write_calibration(tmp_path / "cal.cfg")
    cal = ukdale.parse_calibration(tmp_path / "cal.cfg")
    f1 = synth.write_flac(tmp_path / "x", 1363546800, 400000, seconds=6, seed=1)
    f2 = synth.write_flac(tmp_path / "x", 1363546806, 400000, seconds=6, seed=2)   # f1 ends mid-window 1363546806
    f3 = synth.write_flac(tmp_path / "x", 1363546860, 0, seconds=4, seed=3)        # a 54 s gap
    files = [str(f1), str(f2), str(f3)]
    ref = local_ref.ukdale_treatment_a(files, cal, cfg)
    parts = S.ukdale_partials_raw(spark, files, (cal.volts_per_adc_step, cal.amps_per_adc_step), 1, 5, ("voltage", "current"), "auto", 2)
    for strat in ("hash", "range"):
        out = S.ukdale_merge(parts, 1, "house_1", strat, 8)
        a, r = tol(cfg, "ukdale")
        c = compare(_write(out, tmp_path / f"o_{strat}"), ref, a, r)
        assert c["ok"], c
    assert ref.n.sum() == (6 + 6 + 4) * 16000                                    # nothing lost or double counted
    refb = local_ref.ukdale_treatment_b(ref, cfg)
    sb = S.treatment_b(S.ukdale_merge(parts, 1, "house_1", "hash", 8), ["i_rms", "p_mean"], 1, 300, "n")
    c = compare(_write(sb, tmp_path / "ob"), refb, a, r)
    assert c["ok"], c


def test_compare_detects_wrong_results():
    a = pd.DataFrame({"equipment_id": "e", "window_id": [1, 2], "x": [1.0, 2.0]})
    b = a.copy(); b.loc[1, "x"] = 2.1
    assert not compare(a, b, 1e-9, 1e-9)["ok"]
    b2 = a.copy(); b2.loc[1, "x"] = np.nan
    assert not compare(a, b2, 1e-9, 1e-9)["ok"]                                  # NaN vs value fails
    assert compare(b2, b2, 1e-9, 1e-9)["ok"]                                     # NaN == NaN accepted
