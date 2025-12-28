import asyncio
import http.server
import os
import socketserver
import threading
import time

import nest_asyncio
import pytest

# Disable uvloop for tests to ensure nest_asyncio works
try:
    import uvloop

    # If uvloop is installed, we must ensure it's NOT the default policy for tests
    # because nest_asyncio doesn't support it fully.
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
except ImportError:
    pass

# Apply nest_asyncio globally to patch asyncio module immediately
nest_asyncio.apply()


@pytest.fixture(scope="session")
def anyio_backend():
    """Configure anyio to use asyncio."""
    return "asyncio"


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

    # Use port 0 to let OS choose a free port
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=frontend_dir, **kwargs)

        def log_message(self, format, *args):
            pass  # Silence logs

    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer(("", port), Handler) as httpd:
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()
        # Give server a moment to start
        time.sleep(0.5)
        yield f"http://localhost:{port}"
        httpd.shutdown()
        server_thread.join()
