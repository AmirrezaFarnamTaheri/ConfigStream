import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(Enum):
    """Event types"""

    PROXY_DISCOVERED = "proxy_discovered"
    PROXY_TESTED = "proxy_tested"
    PROXY_FAILED = "proxy_failed"
    PROXY_VALIDATED = "proxy_validated"
    BATCH_COMPLETED = "batch_completed"
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_COMPLETED = "pipeline_completed"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class Event:
    """Event data structure"""

    type: EventType
    timestamp: datetime
    data: dict[str, Any]
    source: str = "configstream"


class EventBus:
    """Central event bus for pub/sub pattern"""

    def __init__(self):
        self.subscribers: dict[EventType, list[Callable]] = {}
        self.event_history: list[Event] = []
        self.max_history = 1000

    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        """Subscribe to event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable) -> None:
        """Unsubscribe from event type"""
        if event_type in self.subscribers:
            self.subscribers[event_type].remove(handler)

    async def publish(self, event: Event) -> None:
        """Publish event to all subscribers"""
        # Store in history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)

        # Notify subscribers
        if event.type in self.subscribers:
            tasks = [
                asyncio.create_task(handler(event)) for handler in self.subscribers[event.type]
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_history(
        self,
        event_type: EventType | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """Get event history"""
        history = self.event_history
        if event_type:
            history = [e for e in history if e.type == event_type]
        return history[-limit:]
