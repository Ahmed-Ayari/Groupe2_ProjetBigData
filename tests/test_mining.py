import json
import pandas as pd
import pytest
from bigdata import mining, synth
from bigdata.config import ROOT, load_config
from bigdata.prepare import prepare_metropt


def test_episodes_k_consecutive():
    import numpy as np
    f = np.array([0, 1, 1, 0, 1, 1, 1, 1, 0], bool)
    assert mining.episodes(f, 3) == [(6, 7)]


def test_mining_refuses_unverified_incidents(tmp_path, cfg):
    c = json.loads(json.dumps(cfg))
    c["paths"]["results"] = str(tmp_path / "res")
    c["mining"]["split"] = {"train_end": "2020-04-01 02:00:00", "val_end": "2020-04-01 04:00:00"}
    incidents = tmp_path / "unverified.csv"
    incidents.write_text("start,end,label,verified\n2020-04-01,2020-04-02,test,no\n")
    c["mining"]["incidents"] = str(incidents)
    csv = synth.make_metropt_csv(tmp_path / "m.csv", hours=6, step_s=10)
    prepare_metropt(csv, tmp_path / "m.parquet", c)
    out = mining.run(c, tmp_path / "m.parquet")
    assert out["evaluation"].startswith("STOPPED") and "incident" in out["evaluation"]   # no invented dates
    assert "false_alerts_per_day" not in out


def test_published_incidents_are_verified_and_fit_chronological_splits():
    cfg = load_config(ROOT / "configs" / "default.yaml")
    incidents_path = ROOT / cfg["mining"]["incidents"]
    incidents = mining.load_incidents(incidents_path)
    assert incidents is not None
    assert len(incidents) == 4
    assert incidents.source.str.startswith("Failure Information:").all()
    train_end = pd.Timestamp(cfg["mining"]["split"]["train_end"])
    val_end = pd.Timestamp(cfg["mining"]["split"]["val_end"])
    assert (incidents.loc[incidents.end < train_end].shape[0] == 3)
    assert (incidents.loc[(incidents.start >= train_end) & (incidents.end < val_end)].shape[0] == 1)
