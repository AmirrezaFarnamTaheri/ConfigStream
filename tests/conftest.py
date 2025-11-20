import pytest
import asyncio
import nest_asyncio

# Apply nest_asyncio globally
nest_asyncio.apply()


@pytest.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
