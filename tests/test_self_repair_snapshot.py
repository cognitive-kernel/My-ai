import json
from my_ai import self_repair

def test_self_repair_creates_snapshot_before_mutation(monkeypatch, tmp_path):
    proposal_dir=tmp_path/"proposals"; proposal_dir.mkdir()
    monkeypatch.setattr(self_repair, "PROPOSALS", proposal_dir)
    calls=[]
    class R:
        returncode=0; stdout=""; stderr=""
    def git(*args, **kwargs):
        calls.append(args)
        if args[:2]==("rev-parse","HEAD"): return type("R",(),{"returncode":0,"stdout":"abc\n","stderr":""})()
        return R()
    monkeypatch.setattr(self_repair, "_git", git)
    proposal={"id":"1234567890abcdef","base":"abc","patch":"diff --git a/a b/a\n","isolated_tests_passed":True}
    (proposal_dir/"1234567890abcdef.json").write_text(json.dumps(proposal),encoding="utf-8")
    monkeypatch.setattr(self_repair, "_clean_git", lambda: True)
    monkeypatch.setattr(self_repair, "get_bool", lambda *a, **k: True)
    monkeypatch.setattr(self_repair, "assert_mutation_allowed", lambda *a, **k: None)
    monkeypatch.setattr(self_repair, "_tests", lambda *a, **k: (True,"ok"))
    monkeypatch.setattr(self_repair, "execute", lambda *a, **k: 1)
    monkeypatch.setattr(self_repair, "record_decision", lambda *a, **k: None)
    monkeypatch.setattr(self_repair, "notify", lambda *a, **k: None)
    monkeypatch.setattr(self_repair.subprocess, "run", lambda *a, **k: R())
    result=self_repair.apply_repair("1234567890abcdef", True)
    assert result["status"]=="applied"
    assert any(args[:3]==("tag","-a","myai-repair-pre-1234567890ab") for args in calls)
