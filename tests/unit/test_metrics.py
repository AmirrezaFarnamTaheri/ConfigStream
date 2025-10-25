"""Tests for metrics collection."""

import json
import tempfile
from pathlib import Path


from configstream.metrics import PipelineMetrics, export_metrics


def test_pipeline_metrics_init():
    """Test metrics initialization."""
    metrics = PipelineMetrics()

    assert metrics.total_sources == 0
    assert metrics.total_tested == 0
    assert metrics.cache_hits == 0


def test_pipeline_metrics_to_dict():
    """Test metrics to dictionary conversion."""
    metrics = PipelineMetrics(
        total_sources=10,
        total_tested=100,
        total_working=80,
        success_rate=0.8,
    )

    data = metrics.to_dict()

    assert data["counters"]["total_sources"] == 10
    assert data["counters"]["total_tested"] == 100
    assert data["rates"]["success_rate_pct"] == 80.0


def test_metrics_save_to_file():
    """Test saving metrics to file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir)
        metrics = PipelineMetrics(total_tested=50)

        metrics.save_to_file(output_path)

        metrics_file = output_path / "metrics.json"
        assert metrics_file.exists()

        with open(metrics_file) as f:
            data = json.load(f)

        assert data["counters"]["total_tested"] == 50


def test_export_metrics():
    """Test metrics export function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir)
        metrics = PipelineMetrics(total_working=30)

        result = export_metrics(metrics, output_path)

        assert Path(result).exists()
