import pytest
from fastapi.testclient import TestClient

from configstream.server import OUTPUT_DIR, app

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    # Should fail if index.html is missing (which it is in the test env likely),
    # but we are testing the route logic.
    # The server code returns FileResponse.
    # If file is missing, Starlette/FastAPI might raise runtime error or 404 depending on implementation.
    # But since we mocked/created dummy files in previous steps or they exist in repo...
    # The repo has frontend/index.html.
    assert response.status_code == 200


def test_websocket_feed_removed():
    """Verify that the websocket endpoint is gone."""
    with pytest.raises(Exception):
        # TestClient.websocket_connect raises if connection is rejected or 404
        with client.websocket_connect("/ws/feed") as websocket:
            websocket.send_text("Hello")


def test_api_stats_endpoint():
    # Ensure metadata.json exists for this test
    meta_path = OUTPUT_DIR / "metadata.json"
    if not meta_path.parent.exists():
        meta_path.parent.mkdir(parents=True)
    meta_path.write_text('{"status": "ok", "last_updated_utc": "2023-01-01T00:00:00Z"}')

    response = client.get("/api/stats")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert "output_dir" in response.json()
