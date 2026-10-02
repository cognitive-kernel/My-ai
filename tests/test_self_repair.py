from my_ai import self_repair


def test_repair_requires_explicit_approval(tmp_path, monkeypatch):
    monkeypatch.setattr(self_repair, "PROPOSALS", tmp_path)
    try:
        self_repair.apply_repair("missing", False)
    except ValueError as exc:
        assert "Explicit approval" in str(exc)
    else:
        raise AssertionError("approval gate was bypassed")


def test_normalize_patch_accepts_fenced_diff():
    patch = self_repair._normalize_patch(chr(96) * 3 + "diff --git a/x b/x\n--- a/x\n+++ b/x\n" + chr(96) * 3)
    assert patch.startswith("diff --git ")


def test_apply_repair_rolls_back_after_post_apply_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(self_repair, "PROPOSALS", tmp_path)
    proposal_id = "rollback-test"
    (tmp_path / f"{proposal_id}.json").write_text(
        '{"id":"rollback-test","base":"base","patch":"diff --git a/x b/x\\n--- a/x\\n+++ b/x\\n","isolated_tests_passed":true,"approved":false,"applied":false}',
        encoding="utf-8",
    )
    calls = []
    def fake_git(*args, **kwargs):
        calls.append(args)
        if args[:2] == ("rev-parse", "HEAD"):
            return type("R", (), {"stdout":"base\n", "returncode":0, "stderr":""})()
        if args[:1] == ("status",):
            return type("R", (), {"stdout":"", "returncode":0, "stderr":""})()
        return type("R", (), {"stdout":"", "returncode":0, "stderr":""})()
    monkeypatch.setattr(self_repair, "_git", fake_git)
    monkeypatch.setattr(self_repair, "_tests", lambda cwd: (False, "forced failure"))
    monkeypatch.setattr(self_repair, "execute", lambda *args, **kwargs: None)
    monkeypatch.setattr(self_repair, "record_decision", lambda *args, **kwargs: None)
    monkeypatch.setattr(self_repair, "notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(self_repair, "assert_mutation_allowed", lambda *args: None)
    monkeypatch.setattr(self_repair, "get_bool", lambda key, default=True: True)
    try:
        self_repair.apply_repair(proposal_id, True)
    except RuntimeError as exc:
        assert "rolled back" in str(exc)
    else:
        raise AssertionError("failed repair was not rolled back")
    assert any(args[:2] == ("reset", "--hard") for args in calls)
