import pytest
import http.server
import socketserver
import threading
import os
import asyncio
import nest_asyncio

# Apply nest_asyncio to allow nested event loops (critical for testing asyncio.run calls)
nest_asyncio.apply()


@pytest.fixture(scope="session", autouse=True)
def apply_nest_asyncio_fixture():
    nest_asyncio.apply()


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
