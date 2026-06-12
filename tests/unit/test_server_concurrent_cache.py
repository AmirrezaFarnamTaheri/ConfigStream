import asyncio
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport

from configstream.server import app, _json_cache, utils

LARGE_JSON_PAYLOAD = {
    "status": "ok",
    "items": [{"id": f"proxy-{i}", "data": "X" * 1000} for i in range(1000)],
}


@pytest.fixture
def metadata_artifact(tmp_path: Path) -> Path:
    file_path = tmp_path / "metadata.json"
    file_path.write_text(json.dumps(LARGE_JSON_PAYLOAD), encoding="utf-8")
    return file_path


@pytest.mark.asyncio
async def test_stats_json_cache_hits_and_invalidates(
    metadata_artifact: Path, monkeypatch
) -> None:
    _json_cache.clear()
    monkeypatch.setenv("OUTPUT_DIR", str(metadata_artifact.parent))

    with (
        patch(
            "configstream.server.utils._read_json_file",
            wraps=utils._read_json_file,
        ) as read_json,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp1 = await client.get("/api/stats")
            assert resp1.status_code == 200
            assert resp1.json()["status"] == "ok"
            assert metadata_artifact in _json_cache
            assert read_json.call_count == 1

            tasks = [client.get("/api/stats") for _ in range(25)]
            responses = await asyncio.gather(*tasks)
            assert all(r.status_code == 200 for r in responses)
            assert read_json.call_count == 1

            current_mtime = metadata_artifact.stat().st_mtime
            updated_payload = {**LARGE_JSON_PAYLOAD, "status": "updated"}
            metadata_artifact.write_text(json.dumps(updated_payload), encoding="utf-8")
            os.utime(
                metadata_artifact,
                (current_mtime + 10.0, current_mtime + 10.0),
            )

            resp_invalidated = await client.get("/api/stats")
            assert resp_invalidated.status_code == 200
            assert resp_invalidated.json()["status"] == "updated"
            assert read_json.call_count == 2

            new_cache_entry = _json_cache[metadata_artifact]
            assert new_cache_entry[0] > current_mtime
