from my_ai.policy_engine import policy

def test_policy_denies_unmapped_mutations_for_non_admin():
    user = {"id": 1, "username": "u", "role": "user"}
    decision = policy.decide(user=user, method="POST", path="/new-write-route", read_only=False)
    assert not decision.allowed
    assert decision.reason == "unmapped_write_or_execute_route"

def test_policy_blocks_mutation_in_read_only():
    user = {"id": 1, "username": "u", "role": "admin"}
    decision = policy.decide(user=user, method="POST", path="/tools/python", read_only=True)
    assert not decision.allowed
    assert decision.reason == "read_only"

def test_policy_allows_public_login():
    decision = policy.decide(user=None, method="POST", path="/auth/login", read_only=True)
    assert decision.allowed


def test_policy_denies_unmapped_reads_for_non_admin():
    user = {"id": 1, "username": "u", "role": "user"}
    decision = policy.decide(user=user, method="GET", path="/unregistered-read-route", read_only=False)
    assert not decision.allowed
    assert decision.reason == "unmapped_route"


def test_policy_denies_unmapped_routes_for_admin_too():
    user = {"id": 1, "username": "admin", "role": "admin"}
    decision = policy.decide(user=user, method="GET", path="/future-unmapped-route", read_only=False)
    assert not decision.allowed
    assert decision.reason == "unmapped_route"
