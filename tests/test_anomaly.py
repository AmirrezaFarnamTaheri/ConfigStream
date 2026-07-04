# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from configstream.anomaly import AnomalyDetector


@pytest.fixture
def anomaly_detector(tmp_path):
    db_path = tmp_path / "anomaly.db"
    return AnomalyDetector(db_path=db_path)


def test_anomaly_detector_init(anomaly_detector):
    assert anomaly_detector.db_path.exists()


def test_is_safe_new_source(anomaly_detector):
    is_safe, reason = anomaly_detector.is_safe("http://new.source", 100)
    assert is_safe is True
    assert reason == "New Source"


def test_is_safe_small_batch(anomaly_detector):
    # Even if it's a spike, small batch is safe
    is_safe, reason = anomaly_detector.is_safe("http://existing.source", 5)
    assert is_safe is True


def test_record_and_history(anomaly_detector):
    url = "http://test.source"
    for _ in range(20):
        anomaly_detector.record(url, 50)

    # Should be safe (stable)
    is_safe, reason = anomaly_detector.is_safe(url, 55)
    assert is_safe is True

    # Should detect spike (Z-Score or Isolation Forest)
    # Force a massive spike
    is_safe, reason = anomaly_detector.is_safe(url, 5000)
    assert is_safe is False
    assert "Spike" in reason or "Outlier" in reason


# ---------------------------------------------------------------------------
# IPv6 subnet flood detection (P1-6 fix coverage)
# ---------------------------------------------------------------------------


def _make_proxy(ip: str) -> dict:
    return {"server": ip}


def test_check_subnet_flood_ipv4_detected(anomaly_detector):
    """IPv4 /24 flood: > 90% from same /24 subnet should be flagged."""
    proxies = [_make_proxy("192.168.1." + str(i % 254 + 1)) for i in range(60)]
    assert anomaly_detector.check_subnet_flood(proxies) is True


def test_check_subnet_flood_ipv4_diverse(anomaly_detector):
    """IPv4 diverse subnets: should not be flagged."""
    proxies = [_make_proxy(f"10.{i}.0.1") for i in range(60)]
    assert anomaly_detector.check_subnet_flood(proxies) is False


def test_check_subnet_flood_ipv6_detected(anomaly_detector):
    """IPv6 /48 flood: > 90% from same /48 block must be detected (P1-6 fix)."""
    # All addresses in 2001:db8:1234::/48 but varying the last 80 bits.
    proxies = [_make_proxy(f"2001:db8:1234::{i:x}") for i in range(1, 61)]
    assert anomaly_detector.check_subnet_flood(proxies) is True


def test_check_subnet_flood_ipv6_diverse(anomaly_detector):
    """IPv6 diverse /48 blocks: should not be flagged."""
    proxies = [_make_proxy(f"2001:db8:{i:04x}::1") for i in range(60)]
    assert anomaly_detector.check_subnet_flood(proxies) is False


def test_check_subnet_flood_mixed_ipv4_ipv6(anomaly_detector):
    """Mixed IPv4 and IPv6 from diverse subnets: should not be flagged."""
    ipv4 = [_make_proxy(f"10.{i}.0.1") for i in range(30)]
    ipv6 = [_make_proxy(f"2001:db8:{i:04x}::1") for i in range(30)]
    assert anomaly_detector.check_subnet_flood(ipv4 + ipv6) is False


def test_check_subnet_flood_below_threshold(anomaly_detector):
    """Fewer than 50 proxies: flood check skips (by design)."""
    proxies = [_make_proxy("192.168.1.1")] * 49
    assert anomaly_detector.check_subnet_flood(proxies) is False


# ---------------------------------------------------------------------------
# get_statistics uses self._conn, not a new connection (P2-5 fix coverage)
# ---------------------------------------------------------------------------


def test_get_statistics_uses_persistent_connection(anomaly_detector):
    """get_statistics must work correctly and use the shared connection."""
    url = "http://stats.test"
    for _ in range(5):
        anomaly_detector.record(url, 100)

    stats = anomaly_detector.get_statistics()
    assert stats["total_sources_tracked"] >= 1
    assert stats["total_history_records"] >= 5
    assert "records_last_24h" in stats
    assert "db_size_bytes" in stats


def test_get_statistics_after_close_returns_empty(anomaly_detector):
    """After close(), get_statistics must return {} gracefully (no new connection opened)."""
    anomaly_detector.close()
    # _conn is now None; get_statistics must not open a new sqlite3.connect().
    stats = anomaly_detector.get_statistics()
    assert stats == {}
