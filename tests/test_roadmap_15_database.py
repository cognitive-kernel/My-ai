from my_ai.settings_store import SETTING_REGISTRY


def test_database_backup_settings_exist():
    expected = {"database.backup_schedule", "database.backup_retention", "database.backup_destination", "database.encryption_enabled"}
    assert expected <= SETTING_REGISTRY.keys()
