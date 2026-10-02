from my_ai import plugin_registry


def test_plugin_registry_exposes_proposal_approval_lifecycle():
    for name in ("propose_plugin", "approve_plugin", "reject_plugin"):
        assert hasattr(plugin_registry, name)
