from configstream.metrics import PipelineMetrics, export_metrics
from pathlib import Path
import json
import time

def test_pipeline_metrics_init():
    metrics = PipelineMetrics()
    assert metrics.total_sources == 0
    assert metrics.start_time > 0

def test_pipeline_metrics_to_dict():
    metrics = PipelineMetrics()
    metrics.total_sources = 10
    metrics.fetch_duration = 5.5
    metrics.success_rate = 0.5
    metrics.protocol_counts = {"vmess": 5}

    data = metrics.to_dict()
    assert data["counters"]["total_sources"] == 10
    assert data["timing"]["fetch_duration_sec"] == 5.5
    assert data["rates"]["success_rate_pct"] == 50.0
    assert data["protocols"]["vmess"] == 5
    assert "timestamp" in data

def test_metrics_throughput_calculation():
    metrics = PipelineMetrics()
    metrics.total_tested = 60
    metrics.test_duration = 60.0 # 1 minute

    data = metrics.to_dict()
    assert data["rates"]["throughput_proxies_per_min"] == 60.0

    metrics.test_duration = 0
    data = metrics.to_dict()
    assert data["rates"]["throughput_proxies_per_min"] == 0

def test_save_metrics(tmp_path):
    metrics = PipelineMetrics(total_working=100)
    path = export_metrics(metrics, tmp_path)

    assert (tmp_path / "metrics.json").exists()
    with open(path) as f:
        data = json.load(f)
        assert data["counters"]["total_working"] == 100
