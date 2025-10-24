import pytest
from concurrent.futures import ThreadPoolExecutor
import configstream.async_file_ops


@pytest.fixture(scope="session", autouse=True)
def file_pool_management():
    """Session-scoped fixture to manage thread pool lifecycle."""
    if configstream.async_file_ops.FILE_IO_POOL._shutdown:
        configstream.async_file_ops.FILE_IO_POOL = ThreadPoolExecutor(
            max_workers=10, thread_name_prefix="configstream-file-io-test"
        )
    yield


@pytest.fixture
def no_pool_shutdown(monkeypatch):
    """Prevent pipeline from shutting down the pool during tests."""
    from unittest.mock import MagicMock

    monkeypatch.setattr(configstream.async_file_ops, "shutdown_file_pool", MagicMock())
    yield
