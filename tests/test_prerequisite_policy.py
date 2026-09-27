def test_prerequisite_policy_request_model_requires_confirmation():
    from my_ai.feature_routes import PrerequisiteRequest
    payload = PrerequisiteRequest(path="x", install_system=True, confirmed=False)
    assert payload.confirmed is False
