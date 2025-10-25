import asyncio
import inspect
from concurrent.futures import ThreadPoolExecutor

import pytest

import configstream.async_file_ops


def pytest_addoption(parser):
    """Provide stubs for coverage options when pytest-cov is unavailable."""

    try:
        __import__("pytest_cov")
        return
    except ModuleNotFoundError:
        pass

    parser.addoption(
        "--cov",
        action="append",
        default=[],
        metavar="PATH",
        help="Stubbed coverage option; install pytest-cov for real coverage",
    )
    parser.addoption(
        "--cov-report",
        action="append",
        default=[],
        metavar="TYPE",
        help="Stubbed coverage report option; install pytest-cov for reports",
    )
    parser.addini(
        "asyncio_mode",
        "Stub ini option so pytest does not warn when pytest-asyncio is unavailable",
        default="auto",
    )


def pytest_configure(config):
    """Register compatibility markers and defaults."""

    config.addinivalue_line("markers", "asyncio: mark a test as requiring the event loop")


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    """Execute ``async`` tests using a minimal event loop implementation."""

    testfunction = pyfuncitem.obj
    if not inspect.iscoroutinefunction(testfunction):
        return None

    signature = inspect.signature(testfunction)
    call_args = {
        name: value for name, value in pyfuncitem.funcargs.items() if name in signature.parameters
    }

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(testfunction(**call_args))
        loop.run_until_complete(loop.shutdown_asyncgens())
    finally:
        asyncio.set_event_loop(None)
        loop.close()

    return True


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
