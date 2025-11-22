import pytest
import asyncio
import nest_asyncio
import importlib.metadata

# Apply nest_asyncio globally to allow nested event loops
nest_asyncio.apply()


@pytest.fixture(scope="session")
def event_loop():
    """
    Create a session-scoped event loop.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def mock_version(monkeypatch):
    """
    Mock importlib.metadata.version to avoid PackageNotFoundError during tests.
    """

    def mock_return(package):
        return "1.2.0"

    monkeypatch.setattr(importlib.metadata, "version", mock_return)
