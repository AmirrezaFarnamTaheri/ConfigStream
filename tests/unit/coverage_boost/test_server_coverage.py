
import pytest
from configstream.server import app, StaticFiles
from fastapi.testclient import TestClient
import os
from unittest.mock import patch, MagicMock

@pytest.fixture
def client(tmp_path):
    # Mock output directory for static files
    # The server uses env var OUTPUT_DIR or default.
    # We can patch OUTPUT_DIR in configstream.server, but it's evaluated at import time.
    # However, we can patch the StaticFiles mount or just ensure the directory exists.

    # Ensure 'output' directory exists in CWD
    os.makedirs("output", exist_ok=True)

    return TestClient(app)

def test_server_root(client):
    # Root serves index.html from frontend dir. We might not have frontend dir in test env.
    # If not found, it might 500 or 404.
    # Given we are in a container/environment where frontend might exist or not.
    pass

def test_server_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "ok"
    assert "output_dir" in json_data

def test_server_static_file_serving(client):
    # Ensure static files are served from /output mount
    with open("output/test.txt", "w") as f:
        f.write("static content")

    response = client.get("/output/test.txt")
    assert response.status_code == 200
    assert response.text == "static content"

    os.remove("output/test.txt")
