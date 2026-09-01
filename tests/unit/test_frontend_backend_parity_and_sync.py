# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for backend-frontend connectedness, parser parity, caches, and sync."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from configstream.hashing import sha256_json
from configstream.models import Proxy
from configstream.parsers.extraction import extract_config_lines
from configstream.parsers.others import parse_hysteria2
from configstream.parsers.shadowsocks import parse_ss
from configstream.parsers.trojan import parse_trojan
from configstream.parsers.vless import parse_vless
from configstream.server import app, _json_cache, utils
from configstream.utils import save_json_file

REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# 1. Backend-Frontend Connectedness & API Contracts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_frontend_backend_health_and_status_contracts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify backend health and status endpoints match frontend contract expectations."""
    _json_cache.clear()
    out_dir = tmp_path / "output"

    def _setup_metadata() -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "status": "ok",
                    "proxy_count": 42,
                    "updated_at": "2026-09-01T00:00:00Z",
                }
            ),
            encoding="utf-8",
        )

    await asyncio.to_thread(_setup_metadata)
    monkeypatch.setattr(utils, "OUTPUT_DIR", out_dir)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        health_data: dict[str, Any] = health_resp.json()
        assert health_data.get("status") in {"ok", "degraded", "healthy"}
        assert "version" in health_data

        live_resp = await client.get("/live")
        assert live_resp.status_code == 200
        live_data: dict[str, Any] = live_resp.json()
        assert live_data.get("status") == "alive"
        assert "version" in live_data


@pytest.mark.asyncio
async def test_frontend_diff_proxy_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify the differential proxy sync contract returns proper delta structure."""
    _json_cache.clear()
    out_dir = tmp_path / "output"

    current_proxies: list[dict[str, Any]] = [
        {"id": "h1", "protocol": "vless", "server": "1.1.1.1", "port": 443},
        {"id": "h2", "protocol": "vmess", "server": "2.2.2.2", "port": 443},
    ]
    old_proxies: list[dict[str, Any]] = [
        {"id": "h1", "protocol": "vless", "server": "1.1.1.1", "port": 443},
        {"id": "h0", "protocol": "trojan", "server": "0.0.0.0", "port": 443},
    ]

    def _setup_diff_files() -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "proxies.json").write_text(
            json.dumps(current_proxies), encoding="utf-8"
        )
        (out_dir / "proxies.old.json").write_text(
            json.dumps(old_proxies), encoding="utf-8"
        )

    await asyncio.to_thread(_setup_diff_files)
    monkeypatch.setattr("configstream.server.routes.proxies.OUTPUT_DIR", out_dir)
    monkeypatch.setattr(utils, "OUTPUT_DIR", out_dir)

    base_version = sha256_json(old_proxies)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        diff_resp = await client.get(f"/api/diff/proxies?base_version={base_version}")
        assert diff_resp.status_code == 200
        diff_data: dict[str, Any] = diff_resp.json()
        assert diff_data.get("type") == "delta"
        assert diff_data.get("base_version") == base_version
        assert diff_data.get("added") == [
            {"id": "h2", "protocol": "vmess", "server": "2.2.2.2", "port": 443}
        ]
        assert diff_data.get("removed") == ["h0"]


# ---------------------------------------------------------------------------
# 2. Multi-Protocol Parser Parity
# ---------------------------------------------------------------------------


def test_parser_parity_across_protocols() -> None:
    """Verify that all core protocol URI parsers extract consistent, schema-compliant Proxy models."""
    sample_uris: dict[str, str] = {
        "vless": "vless://a1b2c3d4-e5f6-4a8b-8c0d-1e2f3a4b5c6d@example.com:443?type=tcp&security=tls#VLESS-Test",
        "trojan": "trojan://password123@example.com:443?security=tls&sni=example.com#Trojan-Test",
        "ss": "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@example.com:8388#Shadowsocks-Test",
        "hysteria2": "hysteria2://user-token@example.com:443/?sni=example.com#Hysteria2-Test",
    }

    nodes: list[Proxy] = []
    for proto, uri in sample_uris.items():
        extracted, _ = extract_config_lines(uri)
        assert len(extracted) == 1, f"Failed to extract {proto} URI"
        line = extracted[0]

        if proto == "vless":
            node = parse_vless(line)
        elif proto == "trojan":
            node = parse_trojan(line)
        elif proto == "ss":
            node = parse_ss(line)
        elif proto == "hysteria2":
            node = parse_hysteria2(line)
        else:
            node = None

        assert node is not None, f"Parser returned None for {proto}"
        assert node.address == "example.com"
        assert node.port in {443, 8388}
        assert node.protocol in {proto, "shadowsocks", "ss"}
        if proto == "vless":
            assert node.uuid == "a1b2c3d4-e5f6-4a8b-8c0d-1e2f3a4b5c6d"
        nodes.append(node)

    assert len(nodes) == 4
    for node in nodes:
        d: dict[str, Any] = node.model_dump()
        assert isinstance(d, dict)
        assert d.get("protocol") == node.protocol
        assert d.get("address") == "example.com"
        assert "details" in d
        assert isinstance(d["details"], dict)


# ---------------------------------------------------------------------------
# 3. Cache Invalidation & Concurrent Access
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_json_cache_concurrency_and_invalidation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify asynchronous JSON cache maintains single-read concurrency and mtime invalidation."""
    _json_cache.clear()
    out_dir = tmp_path / "output"
    data_file = out_dir / "metadata.json"
    initial_payload: dict[str, Any] = {"count": 10, "state": "initial"}

    def _setup_initial_metadata() -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        data_file.write_text(json.dumps(initial_payload), encoding="utf-8")

    await asyncio.to_thread(_setup_initial_metadata)
    monkeypatch.setattr(utils, "OUTPUT_DIR", out_dir)
    monkeypatch.setattr("configstream.server.routes.proxies.OUTPUT_DIR", out_dir)

    with patch(
        "configstream.server.utils._read_json_file", wraps=utils._read_json_file
    ) as mock_reader:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Exercise simultaneous cold-cache reads before any warming request
            tasks = [client.get("/api/stats") for _ in range(20)]
            results = await asyncio.gather(*tasks)
            assert all(r.status_code == 200 for r in results)
            assert all(r.json()["count"] == 10 for r in results)
            assert mock_reader.call_count == 1

            # Update file and touch mtime asynchronously
            updated_payload: dict[str, Any] = {"count": 20, "state": "updated"}

            def _update_metadata_and_mtime() -> None:
                data_file.write_text(json.dumps(updated_payload), encoding="utf-8")
                old_mtime = data_file.stat().st_mtime
                os.utime(data_file, (old_mtime + 5.0, old_mtime + 5.0))

            await asyncio.to_thread(_update_metadata_and_mtime)

            resp_updated = await client.get("/api/stats")
            assert resp_updated.status_code == 200
            assert resp_updated.json()["count"] == 20
            assert mock_reader.call_count == 2


# ---------------------------------------------------------------------------
# 4. Sync & Atomic File Writing Invariants
# ---------------------------------------------------------------------------


def test_atomic_json_sync_and_filelock(tmp_path: Path) -> None:
    """Verify atomic state updates maintain data consistency across simulated concurrent writes."""
    target_file = tmp_path / "sync_state.json"

    # Initial state using production atomic writer
    initial_data: dict[str, Any] = {"step": 1, "items": ["a", "b"]}
    save_json_file(initial_data, str(target_file))
    assert target_file.exists()
    state1: dict[str, Any] = json.loads(target_file.read_text(encoding="utf-8"))
    assert state1["step"] == 1

    # Overwrite state atomically using production atomic writer
    step2_data: dict[str, Any] = {"step": 2, "items": ["a", "b", "c"]}
    save_json_file(step2_data, str(target_file))
    state2: dict[str, Any] = json.loads(target_file.read_text(encoding="utf-8"))
    assert state2["step"] == 2
    assert len(state2["items"]) == 3

    # Exercise concurrency: overlapping writers and readers under file locking
    def writer_task(step: int) -> None:
        save_json_file({"step": step, "payload": [step] * 50}, str(target_file))

    def reader_task() -> dict[str, Any]:
        content = target_file.read_text(encoding="utf-8")
        data = json.loads(content)
        assert isinstance(data, dict)
        assert "step" in data
        assert "payload" in data or "items" in data
        if "payload" in data:
            assert all(x == data["step"] for x in data["payload"])
        return data

    with ThreadPoolExecutor(max_workers=8) as pool:
        writer_futures = [pool.submit(writer_task, i) for i in range(3, 15)]
        reader_futures = [pool.submit(reader_task) for _ in range(15)]
        for f_w in writer_futures:
            f_w.result()
        for f_r in reader_futures:
            f_r.result()

    final_state: dict[str, Any] = json.loads(target_file.read_text(encoding="utf-8"))
    assert 3 <= final_state["step"] <= 14
