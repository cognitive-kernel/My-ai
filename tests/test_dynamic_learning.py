import json
from datetime import datetime, timedelta, timezone

from my_ai import dynamic_learning


def test_resolve_learning_target_supports_arbitrary_subjects():
    assert dynamic_learning.resolve_learning_target("یاد بگیر Rust") == "Rust"
    assert dynamic_learning.resolve_learning_target("learn Kubernetes") == "Kubernetes"
    assert dynamic_learning.resolve_learning_target("something else", "Python") == "Python"


def test_ensure_domain_persists_and_registers_new_subject(monkeypatch):
    saved = {}
    monkeypatch.setattr(dynamic_learning, "_load_saved", lambda name: None)
    monkeypatch.setattr(dynamic_learning, "_persist", lambda name, topics, sources, next_review_at=None: saved.update({"name": name, "topics": topics, "sources": sources, "next": next_review_at}))

    class FakeLLM:
        def chat(self, *_args, **_kwargs):
            return json.dumps({
                "topics": [
                    {"topic": "Rust fundamentals", "goal": "Syntax and ownership"},
                    {"topic": "Ownership", "goal": "Borrowing and lifetimes"},
                    {"topic": "Rust fundamentals", "goal": "duplicate"},
                ],
                "sources": ["https://www.rust-lang.org/learn"],
            })

    name = dynamic_learning.ensure_domain("Rust", FakeLLM())
    assert name == "Rust"
    assert len(dynamic_learning.LANGUAGE_CURRICULA["Rust"]) == 2
    assert saved["name"] == "Rust"
    assert saved["topics"][0]["order"] == 1
    assert saved["sources"] == ["https://www.rust-lang.org/learn"]


def test_due_domains_uses_utc_schedule(monkeypatch):
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    monkeypatch.setattr(dynamic_learning, "_ensure_storage", lambda: None)
    monkeypatch.setattr(dynamic_learning, "fetch_all", lambda *_args, **_kwargs: [
        {"name": "Python", "next_review_at": future},
        {"name": "SQL Server", "next_review_at": past},
    ])
    assert dynamic_learning.due_domains() == ["SQL Server"]
