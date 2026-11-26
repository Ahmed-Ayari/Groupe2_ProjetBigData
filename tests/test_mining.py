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


def test_published_incidents_are_verified_and_source_rows_match_uci_numbering():
    cfg = load_config(ROOT / "configs" / "default.yaml")
    incidents_path = ROOT / cfg["mining"]["incidents"]
    incidents = mining.load_incidents(incidents_path)
    assert incidents is not None
    assert len(incidents) == 4
    assert incidents.source.str.startswith("Failure Information:").all()
    assert "#1 4/18/2020 0:00 4/18/2020 23:59" in incidents.iloc[0].source
    assert "#1 5/29/2020 23:30 5/30/2020 6:00" in incidents.iloc[1].source
    assert "#3 6/5/2020 10:00 6/7/2020 14:30" in incidents.iloc[2].source
    assert "#4 7/15/2020 14:30 7/15/2020 19:00" in incidents.iloc[3].source


def test_expanding_incident_evaluation_uses_preincident_training_and_reports_delay(cfg):
    import numpy as np
    times = pd.date_range("2020-04-14", "2020-04-22", freq="5min", inclusive="left")
    rng = np.random.default_rng(2)
    values = rng.normal(0, 0.05, len(times))
    is_incident = (times >= pd.Timestamp("2020-04-18")) & (times <= pd.Timestamp("2020-04-18 03:00"))
    values[is_incident] += 10
    df = pd.DataFrame({"equipment_id": "metro1", "window_id": np.arange(len(times)), "t": times})
    X = pd.DataFrame({"signal": values})
    incidents = pd.DataFrame({"start": [pd.Timestamp("2020-04-18")],
                              "end": [pd.Timestamp("2020-04-18 03:00")]})
    result = mining.evaluate_incidents(df, X, incidents, cfg)
    incident = result["incidents"][0]
    assert incident["detected"]
    assert incident["detection_delay_min"] is not None
    assert incident["training_windows"] > 0 and incident["validation_windows"] > 0
    assert incident["validation_false_alerts_per_day"] <= incident["validation_false_alert_budget_per_day"]
    assert result["claim"] == "detection of an ongoing incident only, never prediction"
    assert "first incident (18 Apr)" in result["note"]
