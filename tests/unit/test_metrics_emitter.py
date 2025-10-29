import json
from pathlib import Path

from configstream.metrics_emitter import MetricsEmitter, HostMetrics


def test_metrics_emitter_writes_to_file(tmp_path):
    output_path = tmp_path / "metrics.jsonl"
    emitter = MetricsEmitter(output_path)

    metrics = [
        HostMetrics("host1", 0.1, 0.2, 0.0, 2),
        HostMetrics("host2", 0.3, 0.4, 0.1, 4),
    ]

    for m in metrics:
        emitter.record(m)

    emitter.write_metrics()

    assert output_path.exists()

    with output_path.open("r") as f:
        lines = f.readlines()
        assert len(lines) == 2

        data1 = json.loads(lines[0])
        assert data1["host"] == "host1"
        assert data1["p50_latency"] == 0.1

        data2 = json.loads(lines[1])
        assert data2["host"] == "host2"
        assert data2["concurrency_limit"] == 4
