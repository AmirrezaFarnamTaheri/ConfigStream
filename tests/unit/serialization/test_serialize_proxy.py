# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from datetime import datetime, timezone

from configstream.models import Proxy
from configstream.serialize import serialize_proxy, to_json


def _proxy(**overrides):
    values = {
        "config": "vless://test",
        "protocol": "vless",
        "address": "1.1.1.1",
        "port": 443,
        "remarks": "test",
    }
    values.update(overrides)
    return Proxy(**values)


def test_serialize_proxy_includes_uuid_when_valid_uuid():
    proxy = _proxy(uuid="123e4567-e89b-12d3-a456-426614174000")
    data = serialize_proxy(proxy)
    assert data["uuid"] == "123e4567-e89b-12d3-a456-426614174000"


def test_serialize_proxy_includes_history():
    proxy = _proxy(uuid="my-unique-id")
    history = [100.0, 120.0]
    data = serialize_proxy(proxy, history_points=history)
    assert data["history"] == history


def test_public_serialization_never_exposes_source_url_or_internal_keys():
    secret_source = "https://provider.example/sub?token=canary-secret"
    proxy = _proxy(
        details={
            "_source": secret_source,
            "_internal": "do-not-publish",
            "request_headers": {"Authorization": "Bearer secret"},
            "raw_payload": "secret payload",
            "transport": "ws",
            "nested": {
                "source_url": secret_source,
                "password": "private-password",
                "safe": "kept",
            },
        }
    )

    data = serialize_proxy(proxy)
    rendered = json.dumps(data, sort_keys=True)

    assert secret_source not in rendered
    assert "canary-secret" not in rendered
    assert "Bearer secret" not in rendered
    assert "private-password" not in rendered
    assert "do-not-publish" not in rendered
    assert data["source"]
    assert len(data["source"]) == 16
    assert data["details"]["transport"] == "ws"
    assert data["details"]["nested"]["safe"] == "kept"


def test_public_source_identifier_is_stable_and_non_reversible():
    source = "https://provider.example/sub?token=secret"
    first = serialize_proxy(_proxy(details={"_source": source}))
    second = serialize_proxy(_proxy(details={"_source": source}))

    assert first["source"] == second["source"]
    assert first["source"] != source
    assert "provider.example" not in first["source"]


def test_to_json_handles_set():
    result = to_json({"tags": {"a", "b", "c"}})
    assert sorted(json.loads(result)["tags"]) == ["a", "b", "c"]


def test_to_json_handles_tuple():
    result = to_json({"values": (1, 2, 3)})
    assert json.loads(result)["values"] == [1, 2, 3]


def test_to_json_handles_datetime():
    dt = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    result = to_json({"timestamp": dt})
    assert "2025-01-15" in json.loads(result)["timestamp"]


def test_to_json_handles_bytes():
    result = to_json({"raw": b"hello"})
    assert json.loads(result)["raw"] == "hello"
