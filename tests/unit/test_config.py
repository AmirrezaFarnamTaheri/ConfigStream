from configstream.config import AppSettings


def test_app_settings_defaults():
    """Test that AppSettings has default values."""
    settings = AppSettings()
    assert settings.TEST_TIMEOUT == 6  # Optimized from 10 to 6 for faster testing
    assert settings.RETEST_TIMEOUT == 6  # Optimized from 8 to 6 for faster testing
    assert settings.BATCH_SIZE == 50
    assert "vmess" in settings.PROTOCOL_COLORS


def test_app_settings_env_override(monkeypatch):
    """Test that AppSettings can be overridden by environment variables."""
    monkeypatch.setenv("TEST_TIMEOUT", "25")
    monkeypatch.setenv("BATCH_SIZE", "100")

    # The AppSettings class reads environment variables at import time,
    # so we need to reload the module to pick up the patched values.
    import importlib
    from configstream import config

    importlib.reload(config)
    settings = config.AppSettings()
    assert settings.TEST_TIMEOUT == 25
    assert settings.BATCH_SIZE == 100
