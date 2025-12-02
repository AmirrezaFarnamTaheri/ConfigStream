"""
Pipeline Stages.
Components for the streaming pipeline.
Refactored into `src/configstream/pipeline_core/` for modularity.
This module now serves as a facade for backward compatibility.
"""

import logging
from .pipeline_core.models import PipelineStats, PipelineResult
from .pipeline_core.producer import source_producer
from .pipeline_core.consumer import processing_consumer
from .auto_detect import auto_detect_and_parse as parse_config
from .security_validator import (
    validate_batch_configs,
    STRICT_POLICY,
    TEST_POLICY,
    SecurityValidator,
)

logger = logging.getLogger(__name__)

# Expose symbols for existing consumers
__all__ = [
    "PipelineStats",
    "PipelineResult",
    "source_producer",
    "processing_consumer",
    "parse_config",
    "validate_batch_configs",
    "STRICT_POLICY",
    "TEST_POLICY",
    "SecurityValidator",
]
