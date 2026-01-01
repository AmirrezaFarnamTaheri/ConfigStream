# SPDX-License-Identifier: AGPL-3.0-or-later
from configstream.metrics_emitter import MetricsEmitter, HostMetrics


def test_record_and_write(tmp_path):
    output_file = tmp_path / "metrics.jsonl"
    emitter = MetricsEmitter(output_path=output_file)

    metric = HostMetrics(
        host="example.com",
        p50_latency=0.1,
        p95_latency=0.2,
        error_rate=0.0,
        concurrency_limit=5,
    )

    emitter.record(metric)

    # Should not be written yet
    assert not output_file.exists()

    emitter.write_metrics()

    assert output_file.exists()
    content = output_file.read_text()
    assert "example.com" in content
    assert "p50_latency" in content
