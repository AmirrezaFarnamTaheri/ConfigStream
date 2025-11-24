import nest_asyncio
import pytest

# Apply nest_asyncio to allow nested event loops (critical for testing async code that runs other async code)
nest_asyncio.apply()


# Configure pytest-asyncio to handle event loops automatically
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
