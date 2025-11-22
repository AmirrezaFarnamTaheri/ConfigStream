import pytest
import asyncio
import nest_asyncio
import importlib.metadata

# Apply nest_asyncio globally to allow nested event loops
nest_asyncio.apply()


@pytest.fixture(scope="function")
def event_loop():
    """
    Create a function-scoped event loop.
    This overrides the default pytest-asyncio loop fixture to ensure we can customize it if needed,
    but crucially, we apply nest_asyncio to it.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()

    nest_asyncio.apply(loop)
    yield loop
    # loop.close() # Don't close running loop if obtained via get_running_loop


@pytest.fixture(autouse=True)
def mock_version(monkeypatch):
    """
    Mock importlib.metadata.version to avoid PackageNotFoundError during tests.
    """

    def mock_return(package):
        return "1.2.0"

    monkeypatch.setattr(importlib.metadata, "version", mock_return)
