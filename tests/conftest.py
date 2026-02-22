import pytest
import asyncio
import nest_asyncio
import threading
import http.server
import socketserver
import time
import httpx
from pathlib import Path

# Apply nest_asyncio globally
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
    try:
        with httpx.Client(trust_env=False) as client:
            for _ in range(50):
                try:
                    client.get(base_url, timeout=0.5)
                    break
                except Exception:
                    time.sleep(0.1)
            else:
                httpd.shutdown()
                httpd.server_close()
                pytest.skip("Loopback HTTP server is unavailable in this environment")
    except Exception:
        httpd.shutdown()
        httpd.server_close()
        raise

    yield base_url

    httpd.shutdown()
    httpd.server_close()
