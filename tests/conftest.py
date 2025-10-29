import asyncio
import inspect
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest
import httpx

try:  # pragma: no cover - dependency availability guard
    import aiohttp
    from aiohttp import web
    from yarl import URL
except ModuleNotFoundError:  # pragma: no cover - tests will be skipped if missing
    aiohttp = None
    web = None
    URL = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

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


@pytest.fixture
def fs(tmp_path, monkeypatch):
    """Lightweight stand-in for the pyfakefs fixture used in upstream tests."""

    class SimpleFS:
        def __init__(self, base_path: Path):
            self.base_path = base_path

        def create_file(self, relative_path: str, contents: str | bytes = "") -> Path:
            target = self.base_path / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(contents, bytes):
                target.write_bytes(contents)
            else:
                target.write_text(contents)
            return target

    monkeypatch.chdir(tmp_path)
    return SimpleFS(tmp_path)


@pytest.fixture
async def http_server_factory():
    """Factory for creating aiohttp servers."""
    if aiohttp is None or web is None:
        pytest.skip("aiohttp is required for http_server_factory fixture")

    runners = []

    async def create_server(app):
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()

        # Get the actual port from the running server's site info
        site = list(runner.sites)[0]
        port = site._server.sockets[0].getsockname()[1]
        server_url = f"http://127.0.0.1:{port}"
        runners.append(runner)
        return server_url

    yield create_server

    for runner in runners:
        await runner.cleanup()


@pytest.fixture
async def http_client_factory(http_server_factory):
    """Factory for creating HTTPX clients."""

    async def create_client(app):
        base_url = await http_server_factory(app)
        return httpx.AsyncClient(base_url=base_url)

    yield create_client


@pytest.fixture
def mocker():
    """Basic replacement for pytest-mock's mocker fixture."""

    from unittest.mock import AsyncMock, MagicMock, Mock, patch

    active_patchers = []

    class SimpleMocker:
        def patch(self, target, *args, **kwargs):
            patcher = patch(target, *args, **kwargs)
            active_patchers.append(patcher)
            return patcher.start()

        def stopall(self):
            while active_patchers:
                active_patchers.pop().stop()

    SimpleMocker.AsyncMock = AsyncMock  # type: ignore[attr-defined]
    SimpleMocker.MagicMock = MagicMock  # type: ignore[attr-defined]
    SimpleMocker.Mock = Mock  # type: ignore[attr-defined]

    helper = SimpleMocker()
    try:
        yield helper
    finally:
        helper.stopall()
