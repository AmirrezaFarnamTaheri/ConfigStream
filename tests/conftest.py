import pytest
import nest_asyncio
import importlib.metadata


@pytest.fixture(scope="session", autouse=True)
def apply_nest_asyncio():
    nest_asyncio.apply()


@pytest.fixture(autouse=True)
def mock_version(monkeypatch):
    """
    Mock importlib.metadata.version to avoid PackageNotFoundError during tests.
    """

    def mock_return(package):
        return "1.2.0"

    monkeypatch.setattr(importlib.metadata, "version", mock_return)
