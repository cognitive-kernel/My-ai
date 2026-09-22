from my_ai.security import SecurityEngine

class FakeLLM:
    def chat(self,*args,**kwargs):
        return "fixed = True"

def test_security_scan_detects_common_issues():
    code = '''
password = "super-secret-value"
eval(user_input)
subprocess.run(command, shell=True)
cursor.execute(f"SELECT * FROM users WHERE id={user_id}")
'''
    result = SecurityEngine(FakeLLM()).scan_code(code)
    rules = {x["rule_id"] for x in result["findings"]}
    assert "secret" in rules
    assert "code-exec" in rules
    assert "shell-injection" in rules
    assert "sql-injection" in rules

def test_security_scan_can_fix_code():
    result = SecurityEngine(FakeLLM()).scan_code('eval(user_input)', fix=True)
    assert result["fixed"] is True
    assert result["fixed_code"] == "fixed = True"


def test_security_secret_evidence_is_redacted():
    result = SecurityEngine(FakeLLM()).scan_code('password = "super-secret-value"')
    finding = next(x for x in result["findings"] if x["rule_id"] == "secret")
    assert "[REDACTED]" in finding["evidence"]
    assert "super-secret-value" not in finding["evidence"]
