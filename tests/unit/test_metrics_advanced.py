"""Advanced tests for metrics collection and reporting."""

import json
import tempfile
from pathlib import Path

import pytest

from configstream.metrics import PipelineMetrics, export_metrics


class TestPipelineMetrics:
    """Test PipelineMetrics data class and methods."""

    def test_metrics_initialization(self):
        """Test default metrics initialization."""
        metrics = PipelineMetrics()

        assert metrics.total_sources == 0
        assert metrics.total_fetched == 0
        assert metrics.total_parsed == 0
        assert metrics.total_tested == 0
        assert metrics.total_working == 0
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0

        assert metrics.fetch_duration == 0.0
        assert metrics.parse_duration == 0.0
        assert metrics.test_duration == 0.0
        assert metrics.geo_duration == 0.0
        assert metrics.total_duration == 0.0

        assert metrics.success_rate == 0.0
        assert metrics.cache_hit_rate == 0.0
        assert metrics.avg_latency == 0.0

        assert metrics.protocol_counts == {}

    def test_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = PipelineMetrics(
            total_sources=10,
            total_fetched=1000,
            total_parsed=800,
            total_tested=500,
            total_working=400,
            cache_hits=100,
            cache_misses=50,
            fetch_duration=10.5,
            parse_duration=5.2,
            test_duration=120.8,
            geo_duration=8.3,
            total_duration=150.0,
            success_rate=0.8,
            cache_hit_rate=0.67,
            avg_latency=123.45,
        )
        metrics.protocol_counts = {"vmess": 200, "vless": 150, "shadowsocks": 50}

        result = metrics.to_dict()

        assert result["counters"]["total_sources"] == 10
        assert result["counters"]["total_fetched"] == 1000
        assert result["counters"]["cache_hits"] == 100

        assert result["timing"]["fetch_duration_sec"] == 10.5
        assert result["timing"]["test_duration_sec"] == 120.8

        assert result["rates"]["success_rate_pct"] == 80.0
        assert result["rates"]["cache_hit_rate_pct"] == 67.0
        assert result["rates"]["average_latency_ms"] == 123.45

        assert result["protocols"]["vmess"] == 200

        assert "timestamp" in result

    def test_metrics_save_to_file(self):
        """Test saving metrics to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)

            metrics = PipelineMetrics(total_sources=5, total_working=100)

            metrics.save_to_file(output_path)

            metrics_file = output_path / "metrics.json"
            assert metrics_file.exists()

            with open(metrics_file) as f:
                data = json.load(f)

            assert data["counters"]["total_sources"] == 5
            assert data["counters"]["total_working"] == 100

    def test_export_metrics(self):
        """Test export_metrics function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)

            metrics = PipelineMetrics(total_tested=500)

            result_path = export_metrics(metrics, output_path)

            assert result_path == str(output_path / "metrics.json")
            assert Path(result_path).exists()

    def test_throughput_calculation(self):
        """Test throughput calculation in rates."""
        metrics = PipelineMetrics(total_tested=600, test_duration=60.0)  # 1 minute

        result = metrics.to_dict()

        # 600 proxies / 1 minute = 600 proxies per minute
        assert result["rates"]["throughput_proxies_per_min"] == 600.0

    def test_throughput_zero_duration(self):
        """Test throughput when duration is zero."""
        metrics = PipelineMetrics(total_tested=100, test_duration=0.0)

        result = metrics.to_dict()

        # Should not crash with division by zero
        assert result["rates"]["throughput_proxies_per_min"] == 0.0

    def test_metrics_with_protocol_distribution(self):
        """Test metrics with protocol distribution."""
        metrics = PipelineMetrics()
        metrics.protocol_counts = {
            "vmess": 500,
            "vless": 300,
            "shadowsocks": 200,
            "trojan": 150,
            "hysteria2": 100,
        }

        result = metrics.to_dict()

        assert result["protocols"]["vmess"] == 500
        assert result["protocols"]["vless"] == 300
        assert len(result["protocols"]) == 5

    def test_metrics_rounding(self):
        """Test that floating point values are properly rounded."""
        metrics = PipelineMetrics(
            fetch_duration=10.123456789, success_rate=0.876543, avg_latency=123.456789
        )

        result = metrics.to_dict()

        # Should be rounded to 2 decimal places
        assert result["timing"]["fetch_duration_sec"] == 10.12
        assert result["rates"]["success_rate_pct"] == 87.65
        assert result["rates"]["average_latency_ms"] == 123.46

    def test_metrics_json_serializable(self):
        """Test that metrics dict is JSON serializable."""
        metrics = PipelineMetrics(total_sources=10, total_working=100)
        metrics.protocol_counts = {"vmess": 50}

        result = metrics.to_dict()

        # Should not raise
        json_str = json.dumps(result)
        assert json_str is not None

        # Should be able to load it back
        loaded = json.loads(json_str)
        assert loaded["counters"]["total_sources"] == 10
