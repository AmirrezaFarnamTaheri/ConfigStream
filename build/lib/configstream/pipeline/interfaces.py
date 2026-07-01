# SPDX-License-Identifier: AGPL-3.0-or-later
from abc import ABC, abstractmethod
from typing import Any

# Canonical FetchResult lives in fetcher_worker; re-exported here so the
# pipeline package exposes a single, consistent result type.
from configstream.fetcher_worker import FetchResult


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
