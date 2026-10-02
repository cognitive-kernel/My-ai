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
