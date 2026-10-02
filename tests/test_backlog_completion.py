import json

from my_ai import db
from my_ai.access_policy import PATH_ACTIONS, PUBLIC_PATHS, permission_for_path
from my_ai.skill_engine import ensure_skill, record_evidence, revalidate, snapshot


def test_sensitive_route_policy_is_explicit_and_non_public():
    sensitive = {path for method, path in PATH_ACTIONS if method in {"POST", "PUT", "PATCH", "DELETE"}}
    assert sensitive
    assert sensitive.isdisjoint(PUBLIC_PATHS)
    assert all(permission_for_path(path, method) for method, path in PATH_ACTIONS)


def test_skill_lifecycle_invalidates_stale_evidence(tmp_path):
    old = db.settings.db_path
    object.__setattr__(db.settings, "db_path", str(tmp_path / "skills.db"))
    db.init_db()
    try:
        skill_id = ensure_skill("Python", "1.0")
        base = {"command": "pytest tests/test_python.py", "artifact": "artifact-1", "skill_score": 90, "coverage_score": 90, "source_score": 90, "reliability_score": 90}
        official = {"source_url": "https://docs.python.org/3/", "coverage_score": 90, "source_score": 90}
        record_evidence(skill_id, "test", True, base)
        record_evidence(skill_id, "benchmark", True, {**base, "artifact": "benchmark-1"})
        record_evidence(skill_id, "official_source", True, official)
        result = revalidate(skill_id, "2.0")
        assert result["verified"] is False
        assert result["reason"] == "skill_version_changed"
        assert snapshot()[0]["verified"] is False
    finally:
        object.__setattr__(db.settings, "db_path", old)


def test_skill_evidence_hash_is_stored_and_verifiable(tmp_path):
    old = db.settings.db_path
    object.__setattr__(db.settings, "db_path", str(tmp_path / "evidence.db"))
    db.init_db()
    try:
        skill_id = ensure_skill("Rust", "1.0")
        record_evidence(skill_id, "test", True, {"command": "pytest", "artifact": "x", "skill_score": 90})
        raw = db.fetch_all("SELECT evidence FROM skill_evidence WHERE skill_id=?", (skill_id,))[0]["evidence"]
        details = json.loads(raw)
        assert details["evidence_hash"]
        assert details["skill_version"] == "1.0"
        assert details["observed_at"]
    finally:
        object.__setattr__(db.settings, "db_path", old)


import pytest
from pathlib import Path
from types import SimpleNamespace
from my_ai.capability_policy import CAPABILITIES, capability_allowed, inventory
from my_ai.eval_harness import score_skill_verification
from my_ai.model_manager import ModelManager, ModelStatus
from my_ai.policy_engine import policy
from my_ai.resource_guard import limits
from my_ai.scheduler import StudyScheduler
from my_ai.session_lifecycle import append_event, close_stream, create_session, open_stream, reconnect_stream, stream_chunk, verify_integrity
from my_ai import audit_tools
from my_ai import self_repair


def test_model_health_retry_and_multi_step_fallback(monkeypatch):
    manager = ModelManager(); calls = []
    def fail(*args, **kwargs): calls.append(1); raise __import__("httpx").HTTPError("boom")
    monkeypatch.setattr("my_ai.model_manager.httpx.get", fail)
    monkeypatch.setattr("my_ai.model_manager.time.sleep", lambda *_: None)
    status = manager.health("missing", attempts=3)
    assert not status.available and len(calls) == 3
    monkeypatch.setattr(manager, "available_models", lambda **_: {"a", "b", "c"})
    monkeypatch.setattr("my_ai.model_manager.settings", SimpleNamespace(fallback_model="a", ollama_model="b", coding_model="c", routing_model="c"))
    assert manager.fallback_chain("primary") == ["a", "b", "c"]


def test_model_fallback_preserves_history(monkeypatch):
    from my_ai.infra import llm
    settings = llm._settings()
    for key, value in {"ollama_base_url":"http://127.0.0.1:11434","llm_retry_attempts":1,"llm_max_fallback_models":2,"ollama_model":"primary","fallback_model":"fallback","coding_model":"primary","routing_model":"primary"}.items(): object.__setattr__(settings, key, value)
    class FakeManager:
        def health(self, model, **kwargs): return ModelStatus("ollama", model, True, 1.0)
        def fallback_chain(self, model, **kwargs): return ["fallback"]
        def choose_fallback(self, model, **kwargs): return "fallback"
    monkeypatch.setattr(llm, "ModelManager", FakeManager)
    monkeypatch.setattr(llm, "record_inference", lambda *a, **k: None); monkeypatch.setattr(llm, "record_error", lambda *a, **k: None); monkeypatch.setattr(llm, "record_route", lambda *a, **k: None)
    calls=[]
    class Stream:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def raise_for_status(self):
            if len(calls) == 1: raise llm.httpx.HTTPError("primary failed")
        def iter_lines(self): yield '{"message":{"content":"ok"},"done":true}'
    monkeypatch.setattr(llm.httpx, "stream", lambda method,url,**kwargs: (calls.append(kwargs["json"]) or Stream()))
    client=llm.OllamaClient(); client.model="primary"; client.fallback_chain=["fallback"]
    assert "".join(client.stream_chat("سؤال", history=[{"role":"user","content":"قبلی"}])) == "ok"
    assert calls[-1]["model"] == "fallback" and calls[-1]["messages"][0]["content"] == "قبلی"


def test_self_repair_approval_and_clean_tree_guard(monkeypatch, tmp_path):
    monkeypatch.setattr(self_repair, "get_bool", lambda key, default=True: True)
    with pytest.raises(ValueError, match="approval"): self_repair.apply_repair("missing", approved=False, approver_id=None)
    monkeypatch.setattr(self_repair, "_git", lambda *a, **k: type("R",(),{"stdout":"abc\\n","stderr":"","returncode":0})())
    monkeypatch.setattr(self_repair, "_clean_git", lambda: False)
    monkeypatch.setattr(self_repair, "PROPOSALS", tmp_path)
    (tmp_path/"p.json").write_text(json.dumps({"id":"p","base":"abc","isolated_tests_passed":True,"patch":"diff --git a/x b/x"}), encoding="utf-8")
    with pytest.raises(ValueError, match="clean|HEAD changed"): self_repair.apply_repair("p", approved=True, approver_id=1)


def test_capabilities_and_policy_deny_by_default():
    assert all(not capability_allowed(None, name, "read") for name in CAPABILITIES)
    assert not capability_allowed({"role":"user"}, "self-repair", "execute")
    assert capability_allowed({"role":"admin"}, "self-repair", "execute")
    assert inventory(); assert not policy.decide(user=None, method="POST", path="/tools/python", read_only=False).allowed


def test_session_reconnect_integrity_and_cross_user_isolation(client_db):
    owner=create_session(user_id=1); other=create_session(user_id=2)
    assert append_event(owner,"message",{"text":"one"},user_id=1)["sequence"] == 1
    with pytest.raises(ValueError): append_event(owner,"message",{"text":"no"},user_id=2)
    stream=open_stream(owner,"context",user_id=1); assert stream_chunk(stream["stream_id"],"part",1,user_id=1)["sequence"] == 1
    with pytest.raises(ValueError): stream_chunk(stream["stream_id"],"wrong",3,user_id=1)
    close_stream(stream["stream_id"],"interrupted",user_id=1); resumed=reconnect_stream(stream["stream_id"],user_id=1)
    assert resumed["context_hash"] == stream["context_hash"]; assert verify_integrity(owner,user_id=1)["valid"]
    with pytest.raises(ValueError): verify_integrity(owner,user_id=2)
    assert other != owner


def test_scheduler_lease_prevents_duplicate_workers(client_db):
    a,b=StudyScheduler(interval_seconds=60),StudyScheduler(interval_seconds=60)
    assert a._acquire_lease("Python"); assert not b._acquire_lease("Python"); a._release_lease("Python"); assert b._acquire_lease("Python"); b._release_lease("Python")


def test_resource_limits_are_bounded(monkeypatch):
    monkeypatch.setenv("RESOURCES_CPU_PERCENT","999"); monkeypatch.setenv("RESOURCES_RAM_PERCENT","-5"); monkeypatch.setenv("RESOURCES_CPU_THREADS","999"); monkeypatch.setenv("RESOURCES_GPU_LAYERS","-3")
    cfg=limits(); assert cfg["cpu_percent"]==100 and cfg["ram_percent"]==1 and cfg["cpu_threads"]==128 and cfg["gpu_layers"]==0


def test_eval_skill_verification_expected_states():
    assert score_skill_verification([True,False],[True,False])==1.0; assert score_skill_verification([True,True],[True,False])==0.5


def test_audits_have_route_and_failure_inventory():
    root=Path(__file__).resolve().parents[1]
    assert isinstance(audit_tools.find_silent_failures(root),list); assert audit_tools.route_inventory(root); assert isinstance(audit_tools.documentation_inventory(root),dict)
