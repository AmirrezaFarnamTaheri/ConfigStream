import pytest
import asyncio
import nest_asyncio

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    nest_asyncio.apply(loop)
    yield loop
    loop.close()
