import nest_asyncio
import pytest
import threading
import http.server
import socketserver
import os
import time
import asyncio

# Apply nest_asyncio globally
nest_asyncio.apply()

# Use Session scope for event loop to avoid overhead and conflicts?
# No, function scope is safer for isolation.
# But we need to ensure the loop used by pytest-asyncio is the one we patched.


@pytest.fixture(scope="function")
def event_loop():
    """
    Custom event loop fixture for pytest-asyncio.
    Ensures nest_asyncio is applied to the loop.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)
    nest_asyncio.apply(loop)

    yield loop

    # Do not close loop if it's the main thread loop?
    # Actually, proper cleanup is good.
    try:
        if not loop.is_closed():
            loop.close()
    except Exception:
        pass


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


@pytest.fixture(scope="session")
def http_server():
    """Start an HTTP server to serve frontend files for E2E tests."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    frontend_dir = os.path.join(project_root, "frontend")

    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=frontend_dir, **kwargs)

        def log_message(self, format, *args):
            pass

    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer(("", port), Handler) as httpd:
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()
        time.sleep(0.5)
        yield f"http://localhost:{port}"
        httpd.shutdown()
