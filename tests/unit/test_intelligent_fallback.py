import pytest
from unittest.mock import patch, MagicMock
from configstream.intelligent_fallback import FallbackManager
from configstream.models import Proxy


def test_fallback_manager_initialization():
    fm = FallbackManager()
    # Should have fallback_path attribute
    assert hasattr(fm, "fallback_path")


def test_save_successful_run_below_threshold():
    fm = FallbackManager()
    proxies = [MagicMock() for _ in range(50)]  # 50 < 100

    with patch("configstream.intelligent_fallback.logger") as mock_logger:
        fm.save_successful_run(proxies, min_count_hard=100)
        mock_logger.warning.assert_called()
        assert "Fallback NOT saved" in mock_logger.warning.call_args[0][0]


def test_save_successful_run_ratio_check():
    fm = FallbackManager()
    proxies = [MagicMock() for _ in range(150)]

    # Mock existing file with high count
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value='{"proxy_count": 1000}'),
        patch("configstream.intelligent_fallback.logger") as mock_logger,
    ):

        # 150 < 500 (0.5 * 1000)
        fm.save_successful_run(proxies, min_count_hard=100, min_count_ratio=0.5)
        mock_logger.warning.assert_called()
        assert "less than" in mock_logger.warning.call_args[0][0]


def test_save_successful_run_success(tmp_path):
    # Use real file system with tmp_path
    fm = FallbackManager(fallback_path=tmp_path / "fallback.json")

    # Create fake proxy objects
    # Mocking Proxy object to have necessary attributes
    p = MagicMock(spec=Proxy)
    p.config = "vless://..."
    p.protocol = "vless"
    p.address = "1.2.3.4"
    p.port = 443
    p.latency = 100
    p.country = "Testland"
    p.country_code = "TL"
    p.city = "TestCity"

    proxies = [p] * 150

    fm.save_successful_run(proxies, min_count_hard=100)

    assert (tmp_path / "fallback.json").exists()

    # Verify content
    import json

    data = json.loads((tmp_path / "fallback.json").read_text())
    assert data["proxy_count"] == 150
    assert len(data["proxies"]) == 150


def test_load_fallback_success(tmp_path):
    fm = FallbackManager(fallback_path=tmp_path / "fallback.json")

    # Create a valid fallback file
    import json

    data = {
        "saved_at": "2023-01-01T00:00:00Z",
        "proxy_count": 1,
        "proxies": [
            {
                "config": "vless://...",
                "protocol": "vless",
                "address": "1.2.3.4",
                "port": 443,
                "latency": 100,
                "country": "TL",
                "country_code": "TL",
                "city": "City",
            }
        ],
    }
    (tmp_path / "fallback.json").write_text(json.dumps(data))

    proxies = fm.load_fallback()
    assert proxies is not None
    assert len(proxies) == 1
    assert proxies[0].address == "1.2.3.4"


def test_load_fallback_missing():
    fm = FallbackManager()
    with patch("pathlib.Path.exists", return_value=False):
        proxies = fm.load_fallback()
        assert proxies is None


def test_load_fallback_corrupt(tmp_path):
    fm = FallbackManager(fallback_path=tmp_path / "fallback.json")
    (tmp_path / "fallback.json").write_text("INVALID JSON")

    proxies = fm.load_fallback()
    assert proxies is None


def test_should_use_fallback():
    fm = FallbackManager()
    assert fm.should_use_fallback(current_working_count=5, threshold=10) is True
    assert fm.should_use_fallback(current_working_count=15, threshold=10) is False
