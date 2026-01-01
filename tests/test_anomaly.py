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
