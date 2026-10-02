from my_ai.advanced_agent import SecureEnvironment


def test_secure_environment_denies_unapproved_operations():
    env = SecureEnvironment(lambda operation: "deny")
    try:
        env.execute("network", lambda: "must-not-run")
    except PermissionError:
        return
    raise AssertionError("denied operation was executed")


def test_secure_environment_allows_explicit_policy_decision():
    env = SecureEnvironment(lambda operation: "allow")
    assert env.execute("read", lambda: 42) == 42


def test_security_catalog_persists_role_capability_and_policies(monkeypatch):
    import my_ai.security_catalog as sc
    records={}
    monkeypatch.setattr(sc, "put_record", lambda ns,name,payload,**kw: records.__setitem__((ns,name),(payload,kw)) or {"namespace":ns,"name":name,"payload":payload,"enabled":kw.get("enabled",True)})
    sc.define_role("admin",["read","write"])
    sc.define_capability("files",["read"],resource="workspace")
    sc.set_permission("admin","workspace",["read"])
    sc.set_network_policy("default",["example.com"],["bad.example"])
    sc.set_filesystem_policy("sandbox",["projects"],write=False)
    sc.set_subprocess_policy("safe",["python"],timeout=12)
    sc.set_self_modification_policy("default",["my_ai/"],require_approval=True,require_tests=True)
    assert ("security.roles","admin") in records
    assert records[("security.self_modification","default")][0]["require_tests"] is True
