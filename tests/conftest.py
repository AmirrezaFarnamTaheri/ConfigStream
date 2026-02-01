import pytest
import asyncio
import nest_asyncio
import threading
import http.server
import socketserver
import time
import requests
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
    port = 8085
    directory = Path("frontend").resolve()

    if not directory.exists():
        pytest.skip("Frontend directory not found")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, format, *args):
            pass  # Silence logs

    httpd = socketserver.TCPServer(("127.0.0.1", port), Handler)

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"

    # Wait for server
    for _ in range(50):
        try:
            requests.get(base_url, timeout=0.5)
            break
        except Exception:
            time.sleep(0.1)
    else:
        pytest.fail("Could not start http_server fixture")

    yield base_url

    httpd.shutdown()
    httpd.server_close()
