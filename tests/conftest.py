import pytest
import sys
import asyncio

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except (AttributeError, NotImplementedError, RuntimeError):
        pass
import nest_asyncio
import threading
import http.server
import socketserver
import time
import httpx
import os
from pathlib import Path

# Opt into the configstream sniffio/anyio compat patches for the test
# environment (they are now gated behind this var instead of running
# unconditionally at import time — see P3 / __init__.py fix).
os.environ.setdefault("CONFIGSTREAM_COMPAT_PATCHES", "1")

from configstream.config import AppSettings

# Apply global patch to AppSettings to dynamically update settings when environment changes in tests
original_getattribute = AppSettings.__getattribute__


class GetAttrGuard:
    def __init__(self):
        self.local = threading.local()

    def is_active(self):
        return getattr(self.local, "active", False)

    def set_active(self, val):
        self.local.active = val


guard = GetAttrGuard()

_cached_settings = None
_cached_env = None


def get_fresh_settings():
    global _cached_settings, _cached_env
    current_env = dict(os.environ)
    if _cached_settings is None or _cached_env != current_env:
        _cached_settings = AppSettings()
        _cached_env = current_env
    return _cached_settings


def test_getattribute(self, name):
    try:
        is_dynamic = original_getattribute(self, "__dict__").get("_dynamic_env", False)
    except AttributeError:
        is_dynamic = False

    if is_dynamic and name in AppSettings.model_fields and not guard.is_active():
        guard.set_active(True)
        try:
            fresh_settings = get_fresh_settings()
            return original_getattribute(fresh_settings, name)
        finally:
            guard.set_active(False)
    return original_getattribute(self, name)


AppSettings.__getattribute__ = test_getattribute  # type: ignore[method-assign]

# Mark global settings instances in the codebase as dynamically env-aware.
# Only configstream.server.utils still holds a module-level AppSettings
# instance; other modules construct settings locally per call.
try:
    import configstream.server.utils as server_utils

    object.__setattr__(server_utils.settings, "_dynamic_env", True)
except (ImportError, AttributeError):
    pass


@pytest.fixture(scope="function")
def event_loop():
    """Create a fresh event loop for each test and apply nest_asyncio to it.

    nest_asyncio is applied per-loop rather than globally (previous behaviour
    called ``nest_asyncio.apply()`` at module level which patched the global
    loop selector and could leak state between test sessions).
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    nest_asyncio.apply(loop)
    yield loop
    asyncio.set_event_loop(None)
    loop.close()


@pytest.fixture(scope="function")
def isolate_asyncio():
    """Isolate asyncio loop for tests that modify loop state significantly."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    nest_asyncio.apply(loop)
    yield loop
    asyncio.set_event_loop(None)
    loop.close()


@pytest.fixture(scope="session")
def http_server():
    """
    Spins up a simple HTTP server serving the 'frontend' directory for E2E tests.
    Returns the base URL string.
    """
    directory = Path("frontend").resolve()

    if not directory.exists():
        pytest.skip("Frontend directory not found")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, format, *args):
            pass  # Silence logs

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    # Bind to an ephemeral port to avoid collisions with local services/tests.
    httpd = ReusableTCPServer(("127.0.0.1", 0), Handler)
    port = int(httpd.server_address[1])

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"

    # Wait for server. Disable env proxy usage so localhost checks stay local.
    session = httpx.Client(trust_env=False)
    try:
        for _ in range(50):
            try:
                session.get(base_url, timeout=0.5)
                break
            except Exception:
                time.sleep(0.1)
        else:
            httpd.shutdown()
            httpd.server_close()
            pytest.skip("Loopback HTTP server is unavailable in this environment")
    finally:
        session.close()

    yield base_url

    httpd.shutdown()
    httpd.server_close()
