from my_ai.settings_store import SETTING_REGISTRY


def test_github_integration_surface_is_exposed():
    import my_ai.git_connector as git_connector
    assert hasattr(git_connector, "GitHubConnector")
    assert hasattr(SETTING_REGISTRY, "keys")
