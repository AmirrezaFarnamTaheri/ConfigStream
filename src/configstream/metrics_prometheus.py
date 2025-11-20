import logging
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    CONTENT_TYPE_LATEST,
    generate_latest,
)

logger = logging.getLogger(__name__)

# Metrics Definitions
PIPELINE_RUNS = Counter(
    "configstream_pipeline_runs_total", "Total number of pipeline runs"
)
PIPELINE_DURATION = Histogram(
    "configstream_pipeline_duration_seconds", "Time spent running the pipeline"
)
PROXIES_FETCHED = Counter(
    "configstream_proxies_fetched_total", "Total proxies fetched from sources"
)
PROXIES_TESTED = Counter("configstream_proxies_tested_total", "Total proxies tested")
PROXIES_WORKING = Gauge(
    "configstream_proxies_working_current", "Current count of working proxies"
)
PROXY_LATENCY = Histogram(
    "configstream_proxy_latency_seconds",
    "Latency distribution of working proxies",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, float("inf")),
)
FETCH_ERRORS = Counter(
    "configstream_fetch_errors_total", "Total errors fetching sources"
)


def get_metrics():
    """Return latest metrics in Prometheus format."""
    return generate_latest(), CONTENT_TYPE_LATEST
