# SPDX-License-Identifier: AGPL-3.0-or-later
"""Public pipeline interface with lazy implementation imports.

Importing :mod:`configstream.pipeline` must remain cheap and must not require
network, GeoIP, or native-tester dependencies until a caller asks for the
corresponding implementation.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from .interfaces import FetchResult, IConsumer, IFetcher, IPipeline, IProducer
from .models import PipelineContext, WorkItem
from .outcomes import PublicationDecision, RunDisposition, RunStatsView, classify_run

_LAZY_EXPORTS = {
    "HttpFetcher": (".fetcher", "HttpFetcher"),
    "StreamingProducer": (".producer", "StreamingProducer"),
    "WorkerConsumer": (".consumer", "WorkerConsumer"),
    "StandardPipeline": (".core", "StandardPipeline"),
    "run_full_pipeline": (".core", "run_full_pipeline"),
    "SingBoxTester": ("configstream.testers", "SingBoxTester"),
    "SourceQualityTracker": ("configstream.source_quality", "SourceQualityTracker"),
    "AnomalyDetector": ("configstream.anomaly", "AnomalyDetector"),
    "EventStream": ("configstream.event_stream", "EventStream"),
    "DEFAULT_BLOCKLIST": ("configstream.security.blocklist", "DEFAULT_BLOCKLIST"),
    "filter_unique_endpoints": ("configstream.filtering", "filter_unique_endpoints"),
    "ProxyHistoryTracker": ("configstream.history.tracker", "ProxyHistoryTracker"),
    "source_producer": (".producer", "source_producer"),
    "processing_consumer": (".consumer", "processing_consumer"),
    "core": (".core", None),
    "producer": (".producer", None),
    "consumer": (".consumer", None),
}


def GeoIPResolver(*args: Any, **kwargs: Any):
    """Construct the optional GeoIP integration only when requested."""
    from configstream.geoip import GeoIPResolver as _GeoIPResolver

    return _GeoIPResolver(*args, **kwargs)


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute = target
    module = import_module(module_name, package=__name__)
    value = module if attribute is None else getattr(module, attribute)
    globals()[name] = value
    return value


__all__ = [
    "IFetcher",
    "IProducer",
    "IConsumer",
    "IPipeline",
    "FetchResult",
    "WorkItem",
    "PipelineContext",
    "PublicationDecision",
    "RunDisposition",
    "RunStatsView",
    "classify_run",
    "HttpFetcher",
    "StreamingProducer",
    "WorkerConsumer",
    "StandardPipeline",
    "run_full_pipeline",
    "SingBoxTester",
    "SourceQualityTracker",
    "AnomalyDetector",
    "EventStream",
    "GeoIPResolver",
    "DEFAULT_BLOCKLIST",
    "filter_unique_endpoints",
    "ProxyHistoryTracker",
    "source_producer",
    "processing_consumer",
]
