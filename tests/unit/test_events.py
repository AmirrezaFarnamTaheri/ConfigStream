from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from configstream.events import Event, EventBus, EventType


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.mark.asyncio
async def test_event_bus_subscribe_and_publish(event_bus: EventBus):
    """Test that a subscriber is called when an event is published."""
    handler = AsyncMock()
    event_bus.subscribe(EventType.PROXY_TESTED, handler)

    event = Event(
        type=EventType.PROXY_TESTED, timestamp=datetime.now(timezone.utc), data={"proxy": "proxy1"}
    )
    await event_bus.publish(event)

    handler.assert_called_once_with(event)


@pytest.mark.asyncio
async def test_event_bus_unsubscribe(event_bus: EventBus):
    """Test that an unsubscribed handler is not called."""
    handler = AsyncMock()
    event_bus.subscribe(EventType.PROXY_TESTED, handler)
    event_bus.unsubscribe(EventType.PROXY_TESTED, handler)

    event = Event(
        type=EventType.PROXY_TESTED, timestamp=datetime.now(timezone.utc), data={"proxy": "proxy1"}
    )
    await event_bus.publish(event)

    handler.assert_not_called()


@pytest.mark.asyncio
async def test_event_bus_history(event_bus: EventBus):
    """Test the event history functionality."""
    event1 = Event(
        type=EventType.PROXY_TESTED, timestamp=datetime.now(timezone.utc), data={"proxy": "proxy1"}
    )
    event2 = Event(
        type=EventType.PROXY_FAILED, timestamp=datetime.now(timezone.utc), data={"proxy": "proxy2"}
    )

    await event_bus.publish(event1)
    await event_bus.publish(event2)

    history = event_bus.get_history()
    assert len(history) == 2
    assert history[0] == event1
    assert history[1] == event2

    tested_history = event_bus.get_history(event_type=EventType.PROXY_TESTED)
    assert len(tested_history) == 1
    assert tested_history[0] == event1

    limited_history = event_bus.get_history(limit=1)
    assert len(limited_history) == 1
    assert limited_history[0] == event2
