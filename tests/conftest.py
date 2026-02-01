import pytest
import asyncio
import nest_asyncio

# Apply nest_asyncio globally
nest_asyncio.apply()

@pytest.fixture(scope="session")
def event_loop():
    """
    Create an instance of the default event loop for each test session.
    We apply nest_asyncio to this loop to allow nested event loops
    (e.g. asyncio.run called from within a test).
    """
    loop = asyncio.new_event_loop()
    nest_asyncio.apply(loop)
    yield loop
    loop.close()

@pytest.fixture(scope="function")
def isolate_asyncio():
    """
    Fixture to isolate asyncio loop for a test.
    Useful if a test modifies loop state significantly.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    nest_asyncio.apply(loop)
    yield loop
    loop.close()
