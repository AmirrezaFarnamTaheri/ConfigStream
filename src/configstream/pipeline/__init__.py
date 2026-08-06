# SPDX-License-Identifier: AGPL-3.0-or-later
from .interfaces import IFetcher, IProducer, IConsumer, IPipeline, FetchResult
from .models import WorkItem, PipelineContext
from .outcomes import PublicationDecision, RunDisposition, RunStatsView, classify_run
from .fetcher import HttpFetcher
from .producer import StreamingProducer
from .consumer import WorkerConsumer
from .core import StandardPipeline, run_full_pipeline
from . import core  # noqa: F401

# Support legacy test patching on configstream.pipeline
from configstream.testers import SingBoxTester
from configstream.source_quality import SourceQualityTracker
from configstream.anomaly import AnomalyDetector
from configstream.event_stream import EventStream
from configstream.geoip import GeoIPResolver
from configstream.security.blocklist import DEFAULT_BLOCKLIST
from configstream.filtering import filter_unique_endpoints
from configstream.history.tracker import ProxyHistoryTracker
from .producer import source_producer
from .consumer import processing_consumer

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
