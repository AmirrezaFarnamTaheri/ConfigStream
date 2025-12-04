import pytest
from configstream.models import Proxy
from configstream.serialize import serialize_proxy


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
