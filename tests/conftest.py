import nest_asyncio
import pytest
import threading
import http.server
import socketserver
import os
import time
import asyncio

# Apply nest_asyncio to allow nested event loops (critical for testing async code that runs other async code)
nest_asyncio.apply()


@pytest.fixture(scope="function", autouse=True)
def apply_nest_asyncio_fixture():
    # Re-apply nest_asyncio to the current loop, just in case
    try:
        loop = asyncio.get_running_loop()
        nest_asyncio.apply(loop)
    except RuntimeError:
        # No running loop, that's fine
        pass


@pytest.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    # Create a new loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # Apply nest_asyncio to this specific loop
    nest_asyncio.apply(loop)
    yield loop
    # Cleanup
    try:
        if not loop.is_closed():
            loop.close()
    except Exception:
        pass


# Playwright browser launch args for containerized/CI environments
@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Override browser launch arguments for CI/container environments."""
    return {
        **browser_context_args,
        "ignore_https_errors": True,
    }


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Override browser launch arguments to disable sandbox for containerized environments."""
    return {
        **browser_type_launch_args,
        "headless": True,
        "args": [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-software-rasterizer",
            "--disable-extensions",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
    }


# HTTP server fixture for E2E tests (to avoid file:// protocol issues with ES6 modules)
@pytest.fixture(scope="session")
def http_server():
    """Start an HTTP server to serve frontend files for E2E tests."""
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    frontend_dir = os.path.join(project_root, "frontend")

    # Find an available port dynamically
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]

    # Create a simple HTTP server
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=frontend_dir, **kwargs)

        def log_message(self, format, *args):
            # Suppress log messages during tests
            pass

    # Allow port reuse
    socketserver.TCPServer.allow_reuse_address = True

    # Start server in a thread
    with socketserver.TCPServer(("", port), Handler) as httpd:
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()

        # Give server time to start
        time.sleep(0.5)

        # Yield the base URL
        yield f"http://localhost:{port}"

        # Shutdown
        httpd.shutdown()
