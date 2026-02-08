# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from datetime import datetime, timezone
from configstream.models import Proxy
from configstream.serialize import serialize_proxy, to_json


def test_serialize_proxy_includes_uuid():
    """Test that UUID is included in serialized output"""
    proxy = Proxy(
        config="vless://test",
        protocol="vless",
        address="1.1.1.1",
        port=443,
        uuid="my-unique-id",
        remarks="test",
    )
    data = serialize_proxy(proxy)
    assert "uuid" in data
    assert data["uuid"] == "my-unique-id"


def test_serialize_proxy_includes_history():
    """Test that history is included"""
    proxy = Proxy(
        config="vless://test",
        protocol="vless",
        address="1.1.1.1",
        port=443,
        uuid="my-unique-id",
    )
    history = [100.0, 120.0]
    data = serialize_proxy(proxy, history_points=history)
    assert "history" in data
    assert data["history"] == history


def test_to_json_handles_set():
    """Test that to_json serializes sets correctly via _json_default."""
    data = {"tags": {"a", "b", "c"}}
    result = to_json(data)
    parsed = json.loads(result)
    assert sorted(parsed["tags"]) == ["a", "b", "c"]


def test_to_json_handles_tuple():
    """Test that to_json serializes tuples as lists."""
    data = {"values": (1, 2, 3)}
    result = to_json(data)
    parsed = json.loads(result)
    assert parsed["values"] == [1, 2, 3]


def test_to_json_handles_datetime():
    """Test that to_json serializes datetime objects."""
    dt = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    data = {"timestamp": dt}
    result = to_json(data)
    parsed = json.loads(result)
    assert "2025-01-15" in parsed["timestamp"]


def test_to_json_handles_bytes():
    """Test that to_json serializes bytes as string."""
    data = {"raw": b"hello"}
    result = to_json(data)
    parsed = json.loads(result)
    assert parsed["raw"] == "hello"
