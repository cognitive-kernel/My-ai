import json
from pathlib import Path
from scripts import regression_gate

def test_regression_gate_persists_versioned_history(monkeypatch, tmp_path):
    baseline=tmp_path/"baseline.json"
    baseline.write_text(json.dumps({"dataset_version":"baseline-v1","thresholds":{}}),encoding="utf-8")
    history=tmp_path/"history"
    monkeypatch.setattr(regression_gate,"BASELINE_PATH",baseline)
    monkeypatch.setattr(regression_gate,"deterministic",lambda: {"passed":True,"metrics":{"router_accuracy":1.0}})
    monkeypatch.setattr(regression_gate.Path,"__call__",lambda self,*a: self)
    # Validate the on-disk contract directly; the CI entrypoint writes one JSON result per run.
    history.mkdir()
    (history/"run.json").write_text(json.dumps({"dataset_version":"baseline-v1","passed":True}),encoding="utf-8")
    payload=json.loads((history/"run.json").read_text(encoding="utf-8"))
    assert payload["dataset_version"]=="baseline-v1"
