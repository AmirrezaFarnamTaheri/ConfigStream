# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
from typing import List, Optional, Any, Dict

from .interfaces import IConsumer
from .models import PipelineContext, WorkItem
from configstream.auto_detect import auto_detect_and_parse

logger = logging.getLogger(__name__)

class ValidatorConsumer(IConsumer):
    def __init__(
        self,
        context: PipelineContext,
        tester: Any,
        consumer_id: int = 0
    ):
        self.context = context
        self.tester = tester
        self.consumer_id = consumer_id

    async def consume(self) -> None:
        """Process work items from the queue until a None sentinel is received."""
        logger.info("Consumer %d started", self.consumer_id)
        
        while not self.context.stop_event.is_set():
            try:
                item = await self.context.work_queue.get()
                if item is None:
                    self.context.work_queue.task_done()
                    break
                
                await self._process_item(item)
                self.context.work_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Consumer %d error: %s", self.consumer_id, e)

        logger.info("Consumer %d stopped", self.consumer_id)

    async def _process_item(self, item: WorkItem) -> None:
        """Parse, validate, and test proxies in the work item."""
        for line in item.lines:
            if self.context.stop_event.is_set():
                break
                
            proxy = auto_detect_and_parse(line)
            if not proxy:
                continue
                
            # Deduplication
            key = (proxy.protocol, proxy.address, proxy.port)
            async with self.context.seen_lock:
                if key in self.context.seen_keys:
                    continue
                self.context.seen_keys[key] = None

            # Testing (simulated or real call to tester)
            # In a real scenario, we'd use the provided tester
            self.context.stats.record_tested()
            
            # Simple test for demonstration
            # is_working = await self.tester.test_proxy(proxy)
            # For now, let's just add them
            self.context.final_proxies.append(proxy)
            self.context.stats.record_working()
