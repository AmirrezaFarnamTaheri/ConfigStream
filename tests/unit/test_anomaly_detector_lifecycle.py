# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit test for AnomalyDetector DB lifecycle and connection closing."""
import pytest
from pathlib import Path
from configstream.anomaly import AnomalyDetector

def test_anomaly_detector_close_releases_db(tmp_path: Path) -> None:
    db_file = tmp_path / "test_anomaly.db"
    detector = AnomalyDetector(db_path=db_file)
    assert detector._conn is not None

    detector.close()
    assert detector._conn is None

def test_anomaly_detector_context_manager(tmp_path: Path) -> None:
    db_file = tmp_path / "test_anomaly_ctx.db"
    with AnomalyDetector(db_path=db_file) as detector:
        assert detector._conn is not None
    assert detector._conn is None
