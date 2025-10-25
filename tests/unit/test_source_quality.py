"""Tests for source quality tracking system."""

import json
import pytest
from configstream.source_quality import SourceQualityTracker
from configstream.models import Proxy


@pytest.fixture
def temp_quality_path(tmp_path):
    """Create a temporary quality tracking path."""
    return tmp_path / "source_quality.json"


@pytest.fixture
def sample_proxies():
    """Create sample proxies for testing."""
    return [
        Proxy(
            config=f"vmess://test{i}",
            protocol="vmess",
            address=f"1.2.3.{i}",
            port=443,
            is_working=(i % 2 == 0),  # 50% working
            latency=100 + i * 50 if i % 2 == 0 else None,
        )
        for i in range(10)
    ]


def test_tracker_initialization(temp_quality_path):
    """Test tracker initialization."""
    tracker = SourceQualityTracker(db_path=temp_quality_path)
    assert tracker.db_path == temp_quality_path
    assert temp_quality_path.parent.exists()


def test_update_source_quality(temp_quality_path, sample_proxies):
    """Test updating source quality metrics."""
    tracker = SourceQualityTracker(db_path=temp_quality_path)

    tracker.update_source_quality("https://example.com/proxies", sample_proxies)

    # Verify data was saved
    assert temp_quality_path.exists()
    data = json.loads(temp_quality_path.read_text())

    assert "https://example.com/proxies" in data
    source_data = data["https://example.com/proxies"]

    assert source_data["total_proxies"] == 10
    assert source_data["working_proxies"] == 5  # 50% working
    assert source_data["success_rate"] == 0.5
    assert source_data["total_fetches"] == 1


def test_update_source_quality_multiple_times(temp_quality_path, sample_proxies):
    """Test updating source quality multiple times."""
    tracker = SourceQualityTracker(db_path=temp_quality_path)

    # Update twice
    tracker.update_source_quality("https://example.com/proxies", sample_proxies)
    tracker.update_source_quality("https://example.com/proxies", sample_proxies)

    data = json.loads(temp_quality_path.read_text())
    source_data = data["https://example.com/proxies"]

    assert source_data["total_fetches"] == 2


def test_update_source_quality_calculates_avg_latency(temp_quality_path):
    """Test that average latency is calculated correctly."""
    tracker = SourceQualityTracker(db_path=temp_quality_path)

    proxies = [
        Proxy(
            config=f"vmess://test{i}",
            protocol="vmess",
            address=f"1.2.3.{i}",
            port=443,
            is_working=True,
            latency=100 * (i + 1),  # 100, 200, 300
        )
        for i in range(3)
    ]

    tracker.update_source_quality("https://example.com/proxies", proxies)

    data = json.loads(temp_quality_path.read_text())
    source_data = data["https://example.com/proxies"]

    # Average should be (100 + 200 + 300) / 3 = 200
    assert source_data["avg_latency"] == 200.0


def test_update_source_quality_with_no_working_proxies(temp_quality_path):
    """Test updating with no working proxies."""
    tracker = SourceQualityTracker(db_path=temp_quality_path)

    proxies = [
        Proxy(
            config=f"vmess://test{i}",
            protocol="vmess",
            address=f"1.2.3.{i}",
            port=443,
            is_working=False,
        )
        for i in range(5)
    ]

    tracker.update_source_quality("https://example.com/proxies", proxies)

    data = json.loads(temp_quality_path.read_text())
    source_data = data["https://example.com/proxies"]

    assert source_data["working_proxies"] == 0
    assert source_data["success_rate"] == 0.0
    assert source_data["avg_latency"] == 0.0


def test_get_source_score_high_quality(temp_quality_path):
    """Test getting score for high-quality source."""
    tracker = SourceQualityTracker(db_path=temp_quality_path)

    # Create high-quality proxies (100% success, low latency)
    proxies = [
        Proxy(
            config=f"vmess://test{i}",
            protocol="vmess",
            address=f"1.2.3.{i}",
            port=443,
            is_working=True,
            latency=50,  # Very low latency
        )
        for i in range(10)
    ]

    tracker.update_source_quality("https://good-source.com", proxies)

    score = tracker.get_source_score("https://good-source.com")

    # Should be high score (close to 100)
    assert score > 80.0


def test_get_source_score_low_quality(temp_quality_path):
    """Test getting score for low-quality source."""
    tracker = SourceQualityTracker(db_path=temp_quality_path)

    # Create low-quality proxies (0% success)
    proxies = [
        Proxy(
            config=f"vmess://test{i}",
            protocol="vmess",
            address=f"1.2.3.{i}",
            port=443,
            is_working=False,
        )
        for i in range(10)
    ]

    tracker.update_source_quality("https://bad-source.com", proxies)

    score = tracker.get_source_score("https://bad-source.com")

    # Should be low score (close to 0)
    assert score < 20.0


def test_get_source_score_unknown_source(temp_quality_path):
    """Test getting score for unknown source."""
    tracker = SourceQualityTracker(db_path=temp_quality_path)

    score = tracker.get_source_score("https://unknown-source.com")

    # Should return neutral score (50.0) for unknown source
    assert score == 50.0


def test_get_top_sources(temp_quality_path):
    """Test getting top sources."""
    tracker = SourceQualityTracker(db_path=temp_quality_path)

    # Create sources with different quality
    good_proxies = [
        Proxy(
            config=f"vmess://test{i}",
            protocol="vmess",
            address=f"1.2.3.{i}",
            port=443,
            is_working=True,
            latency=50,
        )
        for i in range(10)
    ]

    bad_proxies = [
        Proxy(
            config=f"vmess://test{i}",
            protocol="vmess",
            address=f"1.2.3.{i}",
            port=443,
            is_working=False,
        )
        for i in range(10)
    ]

    tracker.update_source_quality("https://good-source.com", good_proxies)
    tracker.update_source_quality("https://bad-source.com", bad_proxies)

    top_sources = tracker.get_top_sources(limit=2)

    assert len(top_sources) == 2
    assert top_sources[0][0] == "https://good-source.com"  # Best source first
    assert top_sources[0][1] > top_sources[1][1]  # First has higher score


def test_get_top_sources_with_limit(temp_quality_path, sample_proxies):
    """Test getting top sources with limit."""
    tracker = SourceQualityTracker(db_path=temp_quality_path)

    # Create 5 sources
    for i in range(5):
        tracker.update_source_quality(f"https://source{i}.com", sample_proxies)

    top_sources = tracker.get_top_sources(limit=3)

    assert len(top_sources) == 3


def test_get_top_sources_empty(temp_quality_path):
    """Test getting top sources when no sources exist."""
    tracker = SourceQualityTracker(db_path=temp_quality_path)

    top_sources = tracker.get_top_sources(limit=10)

    assert top_sources == []


def test_source_score_calculation_components(temp_quality_path):
    """Test source score calculation components."""
    tracker = SourceQualityTracker(db_path=temp_quality_path)

    # Create proxies with known characteristics
    # 80% success rate, 200ms latency
    proxies = [
        Proxy(
            config=f"vmess://test{i}",
            protocol="vmess",
            address=f"1.2.3.{i}",
            port=443,
            is_working=(i < 8),  # 8 out of 10 working
            latency=200 if i < 8 else None,
        )
        for i in range(10)
    ]

    tracker.update_source_quality("https://test-source.com", proxies)

    # Update multiple times to test consistency component
    for _ in range(10):
        tracker.update_source_quality("https://test-source.com", proxies)

    score = tracker.get_source_score("https://test-source.com")

    # Score should be composed of:
    # - Success rate (80%) * 60 = 48 points
    # - Latency component (varies based on sigmoid)
    # - Consistency (10+ fetches) * 10 = 10 points
    # Should be between 50-90
    assert 50.0 <= score <= 90.0


def test_data_persistence(temp_quality_path, sample_proxies):
    """Test that data persists across tracker instances."""
    # First instance
    tracker1 = SourceQualityTracker(db_path=temp_quality_path)
    tracker1.update_source_quality("https://example.com", sample_proxies)

    # Second instance (should load existing data)
    tracker2 = SourceQualityTracker(db_path=temp_quality_path)
    score = tracker2.get_source_score("https://example.com")

    # Should have loaded the data (50% success rate gives around 30-50 points)
    assert 20.0 < score < 60.0


def test_update_source_quality_with_empty_list(temp_quality_path):
    """Test updating with empty proxy list."""
    tracker = SourceQualityTracker(db_path=temp_quality_path)

    tracker.update_source_quality("https://example.com", [])

    data = json.loads(temp_quality_path.read_text())
    source_data = data["https://example.com"]

    assert source_data["total_proxies"] == 0
    assert source_data["working_proxies"] == 0
    assert source_data["success_rate"] == 0.0


def test_latency_calculation_excludes_failed_proxies(temp_quality_path):
    """Test that latency calculation excludes failed proxies."""
    tracker = SourceQualityTracker(db_path=temp_quality_path)

    proxies = [
        Proxy(
            config="vmess://test1",
            protocol="vmess",
            address="1.2.3.1",
            port=443,
            is_working=True,
            latency=100,
        ),
        Proxy(
            config="vmess://test2",
            protocol="vmess",
            address="1.2.3.2",
            port=443,
            is_working=False,
            latency=None,  # Failed proxy has no latency
        ),
        Proxy(
            config="vmess://test3",
            protocol="vmess",
            address="1.2.3.3",
            port=443,
            is_working=True,
            latency=200,
        ),
    ]

    tracker.update_source_quality("https://example.com", proxies)

    data = json.loads(temp_quality_path.read_text())
    source_data = data["https://example.com"]

    # Average latency should only include working proxies: (100 + 200) / 2 = 150
    assert source_data["avg_latency"] == 150.0
