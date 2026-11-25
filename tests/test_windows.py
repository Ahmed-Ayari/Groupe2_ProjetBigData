"""Numerical and temporal tests for B0 (written before any benchmark)."""
import numpy as np
import pandas as pd
import soundfile as sf
import pytest
from bigdata import windows as W, synth, ukdale, local_ref


def test_pedagogic_rms_and_power():
    u, i = np.array([220.0, 220.0]), np.array([2.0, 4.0])
    p = W.uk_block_partials(u, i, np.array([0, 1], dtype=np.int64), 1000)
    r = W.uk_finalize(W.uk_merge(p), 1000, "h")
    assert r.i_rms[0] == pytest.approx(np.sqrt(10))
    assert r.p_mean[0] == pytest.approx(660.0)


def test_global_mean_is_weighted_not_mean_of_means():
    df = pd.DataFrame({"x": [60, 62, 64, 66, 68.0]})
    t = np.zeros(5, dtype=np.int64)
    a = W.block_partials(df.iloc[:2], t[:2], 10, ["x"])
    b = W.block_partials(df.iloc[2:], t[2:], 10, ["x"])
    m = W.merge_partials(pd.concat([a, b]), ["x"])
    assert m["x__mean"][0] == pytest.approx(64.0) and m["x__mean"][0] != 63.5
    assert m["x__std_pop"][0] == pytest.approx(np.std([60, 62, 64, 66, 68]))


def test_window_cut_across_blocks_equals_single_pass():
    rng = np.random.default_rng(1)
    n = 1000
    t = (np.arange(n) * 3 * W.NS).astype(np.int64)
    df = pd.DataFrame({"x": rng.normal(10, 3, n)})
    full = W.merge_partials(W.block_partials(df, t, 300, ["x"]), ["x"])
    parts = pd.concat([W.block_partials(df.iloc[s:s + 137], t[s:s + 137], 300, ["x"]) for s in range(0, n, 137)])
    chunked = W.merge_partials(parts, ["x"])
    np.testing.assert_allclose(chunked.filter(like="x__").to_numpy(), full.filter(like="x__").to_numpy(), rtol=1e-12)


def test_boundary_timestamp_belongs_to_next_window():
    t = np.array([299 * W.NS, 300 * W.NS], dtype=np.int64)
    assert list(W.window_ids(t, 300)) == [0, 1]


def test_single_observation_has_zero_std():
    df = pd.DataFrame({"x": [5.0]})
    m = W.merge_partials(W.block_partials(df, np.array([0], dtype=np.int64), 10, ["x"]), ["x"])
    assert m["x__std_pop"][0] == 0.0 and m["x__n"][0] == 1


def test_empty_interval_has_no_row():
    t = np.array([0, 1, 2000], dtype=np.int64) * W.NS
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
    m = W.merge_partials(W.block_partials(df, t, 300, ["x"]), ["x"])
    assert list(m.window_id) == [0, 6]


def test_treatment_b_time_based_with_gap():
    win = pd.DataFrame({"equipment_id": "e", "window_id": [0, 1, 2, 5, 6], "n": 10, "f": [1., 2, 3, 10, 20]})
    b = W.treatment_b(win, ["f"], 1, 3, "n").set_index("window_id")
    assert b.loc[1, "delta_f"] == 1 and b.loc[0, "prev_missing"] == 1
    assert np.isnan(b.loc[5, "delta_f"]) and b.loc[5, "prev_missing"] == 1       # gap, not "previous row"
    assert b.loc[2, "hist_f"] == pytest.approx(1.5)                              # windows 0,1
    assert b.loc[5, "hist_f"] == pytest.approx(3.0)                              # only window 2 in [2,4]
    assert b.loc[6, "hist_f"] == pytest.approx(10.0)                             # only window 5 in [3,5]


def test_metropt_chunked_equals_in_memory_and_dedup(tmp_path, cfg):
    """Dedup rule: global exact-duplicate removal in the PREPARE step; B0 then reads chunks of the deduplicated file."""
    from bigdata.prepare import prepare_metropt
    csv = synth.make_metropt_csv(tmp_path / "m.csv", hours=2, step_s=10)
    df = pd.read_csv(csv)
    df = pd.concat([df, df.iloc[[5]]])  # exact duplicate row
    df.to_csv(csv, index=False)
    info = prepare_metropt(csv, tmp_path / "m.parquet", cfg)
    assert info["duplicates_removed"] == 1
    a = local_ref.metropt_treatment_a(tmp_path / "m.parquet", cfg)
    ref = df.drop_duplicates().assign(w=lambda d: ((pd.to_datetime(d.timestamp) - pd.Timestamp("1970-01-01")) // pd.Timedelta(1, "s")) // 300)
    g = ref.groupby("w")["TP2"]
    np.testing.assert_allclose(a["TP2__mean"].to_numpy(), g.mean().to_numpy(), rtol=1e-12)
    np.testing.assert_allclose(a["TP2__std_pop"].to_numpy(), g.std(ddof=0).to_numpy(), rtol=1e-9)
    assert a["TP2__n"].sum() == len(ref)


def test_calibration_and_decode_equals_in_memory(tmp_path, cfg):
    synth.write_calibration(tmp_path / "cal.cfg")
    cal = ukdale.parse_calibration(tmp_path / "cal.cfg")
    f = synth.write_flac(tmp_path / "x", 1363546800, 500000, seconds=7)   # starts mid-second: first/last windows incomplete
    got = local_ref.ukdale_treatment_a([f], cal, cfg).set_index("window_id")
    # naive full in-memory computation
    data, rate = sf.read(str(f), dtype="int32", always_2d=True)
    raw = data.astype(float) / 256
    u, i = raw[:, 0] * cal.volts_per_adc_step, raw[:, 1] * cal.amps_per_adc_step
    t = ukdale.file_start_ns(f) + np.arange(len(u)) * (10**9 // rate)
    wid = t // 10**9
    for w in got.index:
        m = wid == w
        assert got.loc[w, "n"] == m.sum()
        assert got.loc[w, "i_rms"] == pytest.approx(np.sqrt(np.mean(i[m] ** 2)), rel=1e-9)
        assert got.loc[w, "p_mean"] == pytest.approx(np.mean(u[m] * i[m]), rel=1e-9)
    assert got.loc[got.index[3], "v_rms"] == pytest.approx(230.0, rel=1e-3)   # calibration sanity


def test_window_cut_between_two_files(tmp_path, cfg):
    synth.write_calibration(tmp_path / "cal.cfg")
    cal = ukdale.parse_calibration(tmp_path / "cal.cfg")
    f1 = synth.write_flac(tmp_path / "a", 1363546800, 400000, seconds=3, seed=1)
    f2 = synth.write_flac(tmp_path / "b", 1363546803, 0, seconds=3, seed=2)       # file 1 ends at .4+3 = 3.4s
    both = local_ref.ukdale_treatment_a([f1, f2], cal, cfg).set_index("window_id")
    assert both.loc[1363546803, "n"] > 0
    assert both.n.sum() == 6 * 16000                                              # nothing lost, nothing double counted
    assert both.index.is_unique


def test_voltage_channel_evidence(tmp_path, cfg):
    synth.write_calibration(tmp_path / "cal.cfg")
    f = synth.write_flac(tmp_path / "x", 1363546800, 0, seconds=6)
    ev = ukdale.verify(str(f), cfg, ukdale.parse_calibration(tmp_path / "cal.cfg"))
    assert ev["voltage_channel_guess"] == "ch0" and ev["subtype"] == "PCM_24"
