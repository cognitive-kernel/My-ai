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
