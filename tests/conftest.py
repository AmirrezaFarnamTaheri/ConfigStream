import asyncio
import inspect
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

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
def aiohttp_client():
    """Minimal implementation of pytest-aiohttp's aiohttp_client fixture."""

    if aiohttp is None or web is None or URL is None:  # pragma: no cover - dependency guard
        pytest.skip("aiohttp is required for aiohttp_client fixture")

    clients: list[SimpleNamespace] = []

    async def create_client(app: web.Application) -> SimpleNamespace:
        server_loop = asyncio.new_event_loop()
        thread = threading.Thread(target=server_loop.run_forever, daemon=True)
        thread.start()

        async def start_server() -> tuple[web.AppRunner, web.TCPSite, str, int]:
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "127.0.0.1", 0)
            await site.start()
            server = site._server  # pragma: no cover - mirrors pytest-aiohttp internals
            if server is None or not server.sockets:
                raise RuntimeError("aiohttp test server failed to start")
            sock = server.sockets[0]
            host, port = sock.getsockname()[:2]
            return runner, site, host, port

        runner, site, host, port = asyncio.run_coroutine_threadsafe(
            start_server(), server_loop
        ).result()

        base_url = f"http://{host}:{port}"
        session = aiohttp.ClientSession()

        def make_url(path: str = "/"):
            path = path or "/"
            if not path.startswith("/"):
                path = "/" + path
            return URL(base_url + path)

        client = SimpleNamespace(
            runner=runner,
            site=site,
            session=session,
            server=SimpleNamespace(make_url=make_url),
            loop=server_loop,
            thread=thread,
        )
        clients.append(client)
        return client

    yield create_client

    if clients:

        async def close_session(session: aiohttp.ClientSession) -> None:
            if not session.closed:
                await session.close()

        for client in clients:
            # Close client session using a dedicated loop
            temp_loop = asyncio.new_event_loop()
            try:
                temp_loop.run_until_complete(close_session(client.session))
            finally:
                temp_loop.close()

            # Shut down the aiohttp server running on its own loop
            asyncio.run_coroutine_threadsafe(client.site.stop(), client.loop).result()
            asyncio.run_coroutine_threadsafe(client.runner.cleanup(), client.loop).result()
            client.loop.call_soon_threadsafe(client.loop.stop)
            client.thread.join()
            client.loop.close()


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
