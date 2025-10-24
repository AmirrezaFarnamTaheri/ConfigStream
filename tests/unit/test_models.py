def test_proxy_latency_ms_property():
    """Test latency_ms property."""
    from configstream.models import Proxy

    proxy = Proxy(config="test", protocol="vmess", address="1.2.3.4", port=443, latency=100.5)

    assert proxy.latency_ms == 100.5

    proxy.latency_ms = 200.0
    assert proxy.latency == 200.0


def test_proxy_id_property():
    """Test id property for scoring."""
    from configstream.models import Proxy

    proxy = Proxy(
        config="test://config", protocol="vmess", address="1.2.3.4", port=443, uuid="test-uuid"
    )

    assert proxy.id == "test-uuid"

    proxy2 = Proxy(config="test://config", protocol="vmess", address="1.2.3.4", port=443)
    assert proxy2.id == "test://config"


def test_proxy_scheme_property():
    """Test scheme property alias."""
    from configstream.models import Proxy

    proxy = Proxy(config="test", protocol="vmess", address="1.2.3.4", port=443)

    assert proxy.scheme == "vmess"


def test_proxy_host_property():
    """Test host property."""
    from configstream.models import Proxy

    proxy = Proxy(config="test", protocol="vmess", address="1.2.3.4", port=443)

    assert proxy.host == "1.2.3.4"


def test_proxy_user_property():
    """Test user property."""
    from configstream.models import Proxy

    proxy = Proxy(config="test", protocol="vmess", address="1.2.3.4", port=443, uuid="test-user")

    assert proxy.user == "test-user"


def test_proxy_sni_property():
    """Test SNI property."""
    from configstream.models import Proxy

    proxy = Proxy(
        config="test",
        protocol="vmess",
        address="1.2.3.4",
        port=443,
        details={"sni": "example.com"},
    )

    assert proxy.sni == "example.com"

    proxy2 = Proxy(config="test", protocol="vmess", address="1.2.3.4", port=443)
    assert proxy2.sni == ""


def test_proxy_alpn_property():
    """Test ALPN property."""
    from configstream.models import Proxy

    proxy = Proxy(
        config="test",
        protocol="vmess",
        address="1.2.3.4",
        port=443,
        details={"alpn": ["h2", "http/1.1"]},
    )

    assert proxy.alpn == ["h2", "http/1.1"]

    proxy2 = Proxy(
        config="test",
        protocol="vmess",
        address="1.2.3.4",
        port=443,
        details={"alpn": "h2"},
    )
    assert proxy2.alpn == ["h2"]

    proxy3 = Proxy(config="test", protocol="vmess", address="1.2.3.4", port=443)
    assert proxy3.alpn == []


def test_proxy_path_property():
    """Test path property."""
    from configstream.models import Proxy

    proxy = Proxy(
        config="test",
        protocol="vmess",
        address="1.2.3.4",
        port=443,
        details={"path": "/ws"},
    )

    assert proxy.path == "/ws"

    proxy2 = Proxy(config="test", protocol="vmess", address="1.2.3.4", port=443)
    assert proxy2.path == ""
