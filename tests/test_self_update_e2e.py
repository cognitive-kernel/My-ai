from my_ai import self_update


def test_self_update_is_deny_by_default(monkeypatch):
    monkeypatch.delenv("MYAI_SELF_UPDATE_ENABLED", raising=False)
    monkeypatch.delenv("MYAI_SELF_UPDATE_APPROVED", raising=False)
    monkeypatch.setattr(self_update, "_git", lambda *args, **kwargs: "")
    monkeypatch.setattr(self_update, "get_setting", lambda *args: "")
    try:
        self_update.apply_confirmed_update()
    except RuntimeError as exc:
        assert "deny-by-default" in str(exc)
    else:
        raise AssertionError("self-update must require explicit enablement")


def test_health_url_rejects_non_loopback():
    for url in ("http://example.com/health", "https://127.0.0.1/health"):
        try:
            self_update._validate_health_url(url)
        except ValueError:
            pass
        else:
            raise AssertionError(url)


def test_health_url_accepts_loopback():
    assert self_update._validate_health_url("http://127.0.0.1:8000/health") == "http://127.0.0.1:8000/health"


def test_candidate_failure_is_recorded(monkeypatch, tmp_path):
    events = []
    monkeypatch.setattr(self_update, "_record_lesson", lambda event, **data: events.append((event, data)))
    self_update._record_lesson("candidate_test_failed", candidate="abc", details="failed")
    assert events[0][0] == "candidate_test_failed"
