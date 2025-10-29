import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from configstream.intelligent_fallback import FallbackManager
from configstream.models import Proxy


@pytest.fixture
def fallback_manager(tmp_path):
    """Fixture for a FallbackManager instance."""
    return FallbackManager(fallback_path=tmp_path / "fallback.json")


def test_save_and_load_fallback(fallback_manager: FallbackManager):
    """Test saving and loading fallback proxies."""
    proxies = [
        Proxy(
            config="vmess://config1",
            protocol="vmess",
            address="test.com",
            port=443,
            latency=100,
            country="USA",
            country_code="US",
            city="New York",
        )
    ]
    fallback_manager.save_successful_run(proxies)

    loaded_proxies = fallback_manager.load_fallback()
    assert loaded_proxies
    assert len(loaded_proxies) == 1
    assert loaded_proxies[0].config == proxies[0].config


def test_should_use_fallback(fallback_manager: FallbackManager):
    """Test the logic for determining when to use fallback."""
    assert fallback_manager.should_use_fallback(current_working_count=5)
    assert not fallback_manager.should_use_fallback(current_working_count=20)


def test_load_fallback_no_file(fallback_manager: FallbackManager):
    """Test loading fallback when the file doesn't exist."""
    assert fallback_manager.load_fallback() is None


def test_save_empty_proxies(fallback_manager: FallbackManager):
    """Test that saving an empty list of proxies does nothing."""
    fallback_manager.save_successful_run([])
    assert not fallback_manager.fallback_path.exists()


def test_load_corrupted_fallback(fallback_manager: FallbackManager):
    """Test loading a corrupted fallback file."""
    fallback_manager.fallback_path.write_text("not json")
    assert fallback_manager.load_fallback() is None
