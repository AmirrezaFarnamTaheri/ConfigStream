# SPDX-License-Identifier: AGPL-3.0-or-later
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
import asyncio
from configstream.models import Proxy

class FetchResult:
    def __init__(
        self,
        success: bool,
        source: str,
        content: str = "",
        error: Optional[str] = None,
        status_code: int = 0,
        duration_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.source = source
        self.content = content
        self.error = error
        self.status_code = status_code
        self.duration_ms = duration_ms
        self.metadata = metadata or {}

class IFetcher(ABC):
    @abstractmethod
    async def fetch(self, source: str) -> FetchResult:
        """Fetch raw content from a source."""
        pass

class IProducer(ABC):
    @abstractmethod
    async def produce(self) -> None:
        """Fetch sources, parse them, and populate the work queue."""
        pass

class IConsumer(ABC):
    @abstractmethod
    async def consume(self) -> None:
        """Process items from the work queue."""
        pass

class IPipeline(ABC):
    @abstractmethod
    async def run(self) -> Any:
        """Run the full pipeline workflow."""
        pass
