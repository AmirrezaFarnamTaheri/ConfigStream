"""Tests for intelligent fallback system."""

import json
import pytest
from pathlib import Path
from configstream.intelligent_fallback import FallbackManager
from configstream.models import Proxy


@pytest.fixture
def temp_fallback_path(tmp_path):
    """Create a temporary fallback path."""
    return tmp_path / "fallback_proxies.json"


@pytest.fixture
def sample_proxies():
    """Create sample proxies for testing."""
    return [
        Proxy(
            config=f"vmess://test{i}",
            protocol="vmess",
            address=f"1.2.3.{i}",
            port=443,
            is_working=True,
            latency=100 + i * 10,
            country="US",
            country_code="US",
            city="New York",
        )
        for i in range(10)
    ]


def test_fallback_manager_init_with_path_string(temp_fallback_path):
    """Test FallbackManager initialization with string path."""
    manager = FallbackManager(fallback_path=str(temp_fallback_path))
    assert manager.fallback_path == temp_fallback_path
    assert temp_fallback_path.parent.exists()


def test_fallback_manager_init_with_path_object(temp_fallback_path):
    """Test FallbackManager initialization with Path object."""
    manager = FallbackManager(fallback_path=temp_fallback_path)
    assert manager.fallback_path == temp_fallback_path
    assert temp_fallback_path.parent.exists()


def test_save_successful_run(temp_fallback_path, sample_proxies):
    """Test saving successful run."""
    manager = FallbackManager(fallback_path=temp_fallback_path)
    manager.save_successful_run(sample_proxies)

    assert temp_fallback_path.exists()
    data = json.loads(temp_fallback_path.read_text())

    assert "saved_at" in data
    assert "proxy_count" in data
    assert "proxies" in data
    assert data["proxy_count"] == len(sample_proxies)
    assert len(data["proxies"]) == len(sample_proxies)


def test_save_successful_run_limits_to_500(temp_fallback_path):
    """Test that save_successful_run limits to 500 proxies."""
    manager = FallbackManager(fallback_path=temp_fallback_path)

    # Create 600 proxies
    many_proxies = [
        Proxy(
            config=f"vmess://test{i}",
            protocol="vmess",
            address=f"1.2.3.{i % 256}",
            port=443,
            is_working=True,
        )
        for i in range(600)
    ]

    manager.save_successful_run(many_proxies)

    data = json.loads(temp_fallback_path.read_text())
    assert len(data["proxies"]) == 500  # Should be limited to 500


def test_save_successful_run_empty_list(temp_fallback_path):
    """Test saving empty proxy list."""
    manager = FallbackManager(fallback_path=temp_fallback_path)
    manager.save_successful_run([])

    # Should not create file for empty list
    assert not temp_fallback_path.exists()


def test_load_fallback_success(temp_fallback_path, sample_proxies):
    """Test loading fallback data successfully."""
    manager = FallbackManager(fallback_path=temp_fallback_path)

    # Save first
    manager.save_successful_run(sample_proxies)

    # Load
    loaded = manager.load_fallback()

    assert loaded is not None
    assert len(loaded) == len(sample_proxies)
    assert all(p.is_working for p in loaded)  # All should be marked as working
    assert loaded[0].config == sample_proxies[0].config


def test_load_fallback_no_file(temp_fallback_path):
    """Test loading fallback when file doesn't exist."""
    manager = FallbackManager(fallback_path=temp_fallback_path)
    loaded = manager.load_fallback()

    assert loaded is None


def test_load_fallback_corrupted_file(temp_fallback_path):
    """Test loading fallback with corrupted JSON."""
    manager = FallbackManager(fallback_path=temp_fallback_path)

    # Write invalid JSON
    temp_fallback_path.write_text("{ invalid json }")

    loaded = manager.load_fallback()
    assert loaded is None


def test_load_fallback_missing_fields(temp_fallback_path):
    """Test loading fallback with missing optional fields."""
    manager = FallbackManager(fallback_path=temp_fallback_path)

    # Create data with missing optional fields
    data = {
        "saved_at": "2025-10-23T00:00:00Z",
        "proxy_count": 1,
        "proxies": [
            {
                "config": "vmess://test",
                "protocol": "vmess",
                "address": "1.2.3.4",
                "port": 443,
                # Missing: latency, country, country_code, city
            }
        ],
    }

    temp_fallback_path.write_text(json.dumps(data))

    loaded = manager.load_fallback()
    assert loaded is not None
    assert len(loaded) == 1
    assert loaded[0].latency is None
    assert loaded[0].country == ""
    assert loaded[0].city == ""


def test_should_use_fallback_below_threshold():
    """Test should_use_fallback returns True below threshold."""
    manager = FallbackManager()

    assert manager.should_use_fallback(5, threshold=10) is True
    assert manager.should_use_fallback(0, threshold=10) is True
    assert manager.should_use_fallback(9, threshold=10) is True


def test_should_use_fallback_above_threshold():
    """Test should_use_fallback returns False above threshold."""
    manager = FallbackManager()

    assert manager.should_use_fallback(10, threshold=10) is False
    assert manager.should_use_fallback(15, threshold=10) is False
    assert manager.should_use_fallback(100, threshold=10) is False


def test_should_use_fallback_at_threshold():
    """Test should_use_fallback at exact threshold."""
    manager = FallbackManager()

    # At threshold should NOT use fallback
    assert manager.should_use_fallback(10, threshold=10) is False


def test_fallback_data_preserves_proxy_attributes(temp_fallback_path):
    """Test that fallback preserves all proxy attributes."""
    manager = FallbackManager(fallback_path=temp_fallback_path)

    original = Proxy(
        config="vmess://detailed",
        protocol="vmess",
        address="5.6.7.8",
        port=8443,
        is_working=True,
        latency=250,
        country="Germany",
        country_code="DE",
        city="Berlin",
    )

    manager.save_successful_run([original])
    loaded = manager.load_fallback()

    assert loaded is not None
    assert len(loaded) == 1
    restored = loaded[0]

    assert restored.config == original.config
    assert restored.protocol == original.protocol
    assert restored.address == original.address
    assert restored.port == original.port
    assert restored.latency == original.latency
    assert restored.country == original.country
    assert restored.country_code == original.country_code
    assert restored.city == original.city
    assert restored.is_working is True  # Should be True from fallback
