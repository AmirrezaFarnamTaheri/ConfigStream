import pytest
import asyncio
import nest_asyncio

# Apply nest_asyncio globally (as a backup, though tests/__init__.py handles Runner)
nest_asyncio.apply()

@pytest.fixture(scope="function")
def event_loop():
    """
    Create an instance of the default event loop for each test.
    Explicitly sets the loop as current to prevent 'Runner.run' conflicts
    and applies nest_asyncio for reentrancy support.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    nest_asyncio.apply(loop)
    yield loop
    asyncio.set_event_loop(None)
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
    asyncio.set_event_loop(None)
    loop.close()
