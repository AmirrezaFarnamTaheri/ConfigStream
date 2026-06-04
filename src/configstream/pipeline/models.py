# SPDX-License-Identifier: AGPL-3.0-or-later
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
import asyncio
from configstream.models import Proxy
from configstream.pipeline_stats import PipelineStats

@dataclass
class WorkItem:
    source: str
    lines: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PipelineContext:
    work_queue: asyncio.Queue[WorkItem]
    stop_event: asyncio.Event
    stats: PipelineStats
    final_proxies: List[Proxy]
    seen_keys: Dict[Tuple[Any, ...], None]
    seen_lock: asyncio.Lock
    settings: Any  # AppSettings
