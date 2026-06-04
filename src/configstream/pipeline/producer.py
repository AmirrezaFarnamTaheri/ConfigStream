# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
from typing import List, Optional, Any, Dict

from .interfaces import IProducer, IFetcher
from .models import PipelineContext, WorkItem
from configstream.parsers import extract_config_lines

logger = logging.getLogger(__name__)

class StreamingProducer(IProducer):
    def __init__(
        self,
        sources: List[str],
        fetcher: IFetcher,
        context: PipelineContext,
        ingest_chunk_size: int = 500,
    ):
        self.sources = sources
        self.fetcher = fetcher
        self.context = context
        self.ingest_chunk_size = ingest_chunk_size

    async def produce(self) -> None:
        """Fetch all sources and put them into the queue."""
        logger.info("Starting producer with %d sources", len(self.sources))
        
        # Parallel fetch with a semaphore or limit if needed
        # For now, let's process them in parallel
        tasks = [self._process_source(source) for source in self.sources]
        await asyncio.gather(*tasks)
        
        logger.info("Producer finished. Sending shutdown signal to consumers.")
        # We don't send None here yet, because multiple producers might exist.
        # Usually, the orchestrator handles sending the sentinels.

    async def _process_source(self, source: str) -> None:
        if self.context.stop_event.is_set():
            return

        result = await self.fetcher.fetch(source)
        
        if not result.success:
            logger.warning("Failed to fetch source %s: %s", source, result.error)
            return

        lines = extract_config_lines(result.content)
        if not lines:
            return

        # Chunk the lines and put into work queue
        for i in range(0, len(lines), self.ingest_chunk_size):
            if self.context.stop_event.is_set():
                break
                
            chunk = lines[i : i + self.ingest_chunk_size]
            item = WorkItem(
                source=source,
                lines=chunk,
                metadata={
                    "chunk_index": (i // self.ingest_chunk_size) + 1,
                    "chunk_total": (len(lines) + self.ingest_chunk_size - 1) // self.ingest_chunk_size
                }
            )
            
            try:
                await asyncio.wait_for(
                    self.context.work_queue.put(item),
                    timeout=5.0 # Bounded put
                )
            except asyncio.TimeoutError:
                logger.warning("Work queue is full, dropping chunk from %s", source)
