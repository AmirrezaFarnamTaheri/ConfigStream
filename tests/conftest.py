import pytest
import http.server
import socketserver
import threading
import os
import asyncio
import nest_asyncio

# Apply nest_asyncio to allow nested event loops (critical for testing asyncio.run calls)
nest_asyncio.apply()

# [FIX] Manually patch Runner.run to support nested loops with nest_asyncio
# This is required because nest_asyncio does not patch asyncio.Runner.run (or backports)
# and pytest-asyncio uses it directly.
def patch_runner_for_nest_asyncio():
    def _patch(runner_cls):
        original_run = runner_cls.run

        def patched_run(self, coro, *, context=None):
            loop = None
            if hasattr(self, 'get_loop'):
                loop = self.get_loop()
            elif hasattr(self, '_loop'):
                loop = self._loop

            if loop and loop.is_running():
                 # Nested execution!
                 # Use ensure_future to schedule on the running loop
                 task = asyncio.ensure_future(coro, loop=loop)

                 # nest_asyncio patched loop.run_until_complete handles reentrancy
                 loop.run_until_complete(task)
                 return task.result()

            return original_run(self, coro, context=context)

        runner_cls.run = patched_run

    # Patch asyncio.Runner (3.11+)
    if hasattr(asyncio, 'Runner'):
        _patch(asyncio.Runner)

    # Patch backports.asyncio.runner.Runner (3.10 and below)
    try:
        import backports.asyncio.runner.runner as backports_runner
        if hasattr(backports_runner, 'Runner'):
            _patch(backports_runner.Runner)
    except ImportError:
        pass

patch_runner_for_nest_asyncio()


@pytest.fixture(scope="session", autouse=True)
def apply_nest_asyncio_fixture():
    nest_asyncio.apply()
    patch_runner_for_nest_asyncio()


@pytest.fixture(scope="session")
def http_server(request):
    """Starts a simple HTTP server to serve the frontend."""
    # Define directory to serve
    frontend_dir = os.path.join(os.getcwd(), "frontend")
    if not os.path.exists(frontend_dir):
        pytest.skip("Frontend directory not found")

    # Port 0 means random available port
    handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer(("localhost", 0), handler)
    port = httpd.server_address[1]

    def serve():
        os.chdir(frontend_dir)
        httpd.serve_forever()
        os.chdir(os.path.dirname(os.getcwd()))  # Restore cwd? unsafe in thread

    # Better way: Custom handler with directory
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=frontend_dir, **kwargs)

    httpd = socketserver.TCPServer(("localhost", 0), Handler)
    port = httpd.server_address[1]

    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    yield f"http://localhost:{port}"

    httpd.shutdown()
    httpd.server_close()
