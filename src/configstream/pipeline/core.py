# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
from typing import List, Optional, Any, Dict

from .interfaces import IPipeline, IProducer, IConsumer
from .models import PipelineContext, WorkItem
from configstream.pipeline_stats import PipelineStats, PipelineResult
from configstream.config import AppSettings

logger = logging.getLogger(__name__)

class StandardPipeline(IPipeline):
    def __init__(
        self,
        sources: List[str],
        producer_factory: Any,
        consumer_factory: Any,
        num_consumers: int = 4
    ):
        self.sources = sources
        self.producer_factory = producer_factory
        self.consumer_factory = consumer_factory
        self.num_consumers = num_consumers
        self.settings = AppSettings()
        
        self.context = PipelineContext(
            work_queue=asyncio.Queue(maxsize=5000),
            stop_event=asyncio.Event(),
            stats=PipelineStats(),
            final_proxies=[],
            seen_keys={},
            seen_lock=asyncio.Lock(),
            settings=self.settings
        )

    async def run(self) -> PipelineResult:
        """Run the pipeline workflow."""
        logger.info("Starting pipeline execution")
        
        # 1. Create Producer and Consumers
        producer = self.producer_factory(self.sources, self.context)
        consumers = [self.consumer_factory(self.context, i) for i in range(self.num_consumers)]
        
        # 2. Start Tasks
        producer_task = asyncio.create_task(producer.produce())
        consumer_tasks = [asyncio.create_task(c.consume()) for c in consumers]
        
        try:
            # 3. Wait for producer to finish
            await producer_task
            
            # 4. Send sentinels to consumers
            for _ in range(self.num_consumers):
                await self.context.work_queue.put(None)
                
            # 5. Wait for consumers to finish
            await asyncio.gather(*consumer_tasks)
            
        except Exception as e:
            logger.exception("Pipeline execution failed: %s", e)
            self.context.stop_event.set()
            raise
            
        logger.info("Pipeline execution completed")
        return PipelineResult(
            success=True,
            stats=self.context.stats,
            output_files=[], # To be filled by output handler
            error=None
        )
