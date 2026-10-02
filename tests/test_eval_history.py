import json
from my_ai.eval_harness import BASELINE_CASES, compare_regression_baseline
import importlib.util
from pathlib import Path

_spec=importlib.util.spec_from_file_location("regression_gate", Path(__file__).parents[1] / "scripts" / "regression_gate.py")
regression_gate=importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(regression_gate)

def test_regression_gate_uses_versioned_baseline(monkeypatch, tmp_path):
    baseline=tmp_path/"baseline.json"
    baseline.write_text(json.dumps({"dataset_version":"baseline-v1","thresholds":{"router_accuracy":0.9}}),encoding="utf-8")
    monkeypatch.setattr(regression_gate,"BASELINE_PATH",baseline)
    monkeypatch.setattr(regression_gate,"run_retrieval_eval",lambda *a,**k: {"mrr":1.0})
    monkeypatch.setattr(regression_gate,"run_response_eval",lambda *a,**k: {"mean_score":1.0})
    result=regression_gate.deterministic()
    assert result["passed"] is True
    assert result["mode"]=="deterministic"

def test_regression_history_payload_is_json_and_versioned():
    result=compare_regression_baseline({"router_accuracy":1.0},{"router_accuracy":0.9})
    payload=json.dumps({"dataset_version":"baseline-v1","result":result},ensure_ascii=False)
    decoded=json.loads(payload)
    assert decoded["dataset_version"]=="baseline-v1"
    assert decoded["result"]["passed"] is True
    assert BASELINE_CASES
