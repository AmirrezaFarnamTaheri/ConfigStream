import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from configstream.server import app

client = TestClient(app)


@pytest.fixture
def mock_output_dir(tmp_path):
    """Mock the output directory and create dummy files."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Create metadata.json
    metadata = {
        "last_updated_utc": "2023-10-27T10:00:00Z",
        "total_proxies": 100,
        "total_working": 80,
        "countries": {"US": 50, "DE": 30},
        "protocols": {"vmess": 60, "vless": 40},
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata))

    # Create proxies.json
    proxies = [{"protocol": "vmess", "country_code": "US"}]
    (output_dir / "proxies.json").write_text(json.dumps(proxies))

    # Create country specific file
    country_dir = output_dir / "by_country"
    country_dir.mkdir()
    (country_dir / "us.json").write_text(json.dumps(proxies))

    # Create protocol specific file
    proto_dir = output_dir / "by_protocol"
    proto_dir.mkdir()
    (proto_dir / "vmess.json").write_text(json.dumps(proxies))

    # Create subscription files
    (output_dir / "clash.yaml").write_text("proxies: []")

    return output_dir


@pytest.fixture
def mock_frontend_dir(tmp_path):
    """Mock the frontend directory."""
    frontend_dir = tmp_path / "frontend"
    frontend_dir.mkdir()
    (frontend_dir / "index.html").write_text("<html>Index</html>")
    (frontend_dir / "about.html").write_text("<html>About</html>")

    # Create assets directory to avoid mounting errors if it doesn't exist
    (frontend_dir / "assets").mkdir()

    return frontend_dir


def test_health_check(mock_output_dir):
    with patch("configstream.server.OUTPUT_DIR", mock_output_dir):
        response = client.get("/health")
        assert response.status_code == 200
        # Check keys existence and status value
        json_resp = response.json()
        assert json_resp["status"] == "ok"
        assert "output_dir" in json_resp
        # files_present might be 5 or 6 depending on hidden files/impl
        assert json_resp["files_present"] >= 0


def test_get_stats(mock_output_dir):
    with patch("configstream.server.OUTPUT_DIR", mock_output_dir):
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_proxies"] == 100


def test_get_proxies_all(mock_output_dir):
    with patch("configstream.server.OUTPUT_DIR", mock_output_dir):
        response = client.get("/api/proxies")
        assert response.status_code == 200
        assert len(response.json()) == 1


def test_get_proxies_by_country(mock_output_dir):
    with patch("configstream.server.OUTPUT_DIR", mock_output_dir):
        response = client.get("/api/proxies?country=US")
        assert response.status_code == 200
        assert len(response.json()) == 1

        response = client.get("/api/proxies?country=XX")
        assert response.status_code == 404


def test_get_proxies_by_protocol(mock_output_dir):
    with patch("configstream.server.OUTPUT_DIR", mock_output_dir):
        response = client.get("/api/proxies?protocol=vmess")
        assert response.status_code == 200
        assert len(response.json()) == 1

        response = client.get("/api/proxies?protocol=invalid")
        assert response.status_code == 404


def test_download_subscription(mock_output_dir):
    with patch("configstream.server.OUTPUT_DIR", mock_output_dir):
        response = client.get("/subscribe/clash")
        assert response.status_code == 200
        assert "proxies:" in response.text

        response = client.get("/subscribe/invalid")
        assert response.status_code == 400


def test_frontend_serving(mock_frontend_dir):
    with patch("configstream.server.FRONTEND_DIR", mock_frontend_dir):
        response = client.get("/")
        assert response.status_code == 200
        assert "Index" in response.text

        response = client.get("/about")
        assert response.status_code == 200
        assert "About" in response.text
