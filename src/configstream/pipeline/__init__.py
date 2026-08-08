# SPDX-License-Identifier: AGPL-3.0-or-later
from importlib import import_module
from typing import Any

from .interfaces import IFetcher, IProducer, IConsumer, IPipeline, FetchResult
from .models import WorkItem, PipelineContext
from .outcomes import PublicationDecision, RunDisposition, RunStatsView, classify_run
from .fetcher import HttpFetcher
from .producer import StreamingProducer, source_producer
from .consumer import WorkerConsumer, processing_consumer

# Preserve legacy public imports and patch targets on configstream.pipeline.
from configstream.testers import SingBoxTester
from configstream.source_quality import SourceQualityTracker
from configstream.anomaly import AnomalyDetector
from configstream.event_stream import EventStream
from configstream.geoip import GeoIPResolver
from configstream.security.blocklist import DEFAULT_BLOCKLIST
from configstream.filtering import filter_unique_endpoints
from configstream.history.tracker import ProxyHistoryTracker

# core.py imports this facade for patchable public collaborators, so eager
# re-exporting the orchestration core here creates a first-party import cycle.
_CORE_EXPORTS = {"StandardPipeline", "run_full_pipeline"}
_PATCH_TARGET_MODULES = {"core", "producer", "consumer"}


def __getattr__(name: str) -> Any:
    if name in _PATCH_TARGET_MODULES:
        module = import_module(f".{name}", __name__)
        globals()[name] = module
        return module
    if name in _CORE_EXPORTS:
        core_module = import_module(".core", __name__)
        value = getattr(core_module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
