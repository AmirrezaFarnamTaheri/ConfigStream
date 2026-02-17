from configstream.models import Proxy
from configstream.converters.singbox import to_singbox_outbound

def test_shadowsocks_obfs_drop():
    """Test that Shadowsocks proxies with 'obfs' plugin are dropped."""
    proxy = Proxy(
        config="ss://method:password@example.com:443",
        protocol="shadowsocks",
        address="example.com",
        port=443,
        uuid="password",
        remarks="test",
        details={
            "method": "chacha20-ietf-poly1305",
            "password": "password",
            "plugin": "obfs",
            "plugin_opts": "obfs=http"
        },
    )
    # Expect None because we don't have the plugin
    assert to_singbox_outbound(proxy) is None

def test_shadowsocks_obfs_local_drop():
    """Test that Shadowsocks proxies with 'obfs-local' plugin are dropped."""
    proxy = Proxy(
        config="ss://method:password@example.com:443",
        protocol="shadowsocks",
        address="example.com",
        port=443,
        uuid="password",
        remarks="test",
        details={
            "method": "chacha20-ietf-poly1305",
            "password": "password",
            "plugin": "obfs-local",
            "plugin_opts": "obfs=http"
        },
    )
    assert to_singbox_outbound(proxy) is None

def test_shadowsocks_simple_obfs_drop():
    """Test that Shadowsocks proxies with 'simple-obfs' plugin are dropped."""
    proxy = Proxy(
        config="ss://method:password@example.com:443",
        protocol="shadowsocks",
        address="example.com",
        port=443,
        uuid="password",
        remarks="test",
        details={
            "method": "chacha20-ietf-poly1305",
            "password": "password",
            "plugin": "simple-obfs",
            "plugin_opts": "obfs=http"
        },
    )
    assert to_singbox_outbound(proxy) is None

def test_shadowsocks_valid_plugin():
    """Test that Shadowsocks proxies with potentially valid plugin (e.g. v2ray-plugin) are NOT dropped by this check."""
    # Note: We only check for obfs-related plugins. Others pass through.
    proxy = Proxy(
        config="ss://method:password@example.com:443",
        protocol="shadowsocks",
        address="example.com",
        port=443,
        uuid="password",
        remarks="test",
        details={
            "method": "chacha20-ietf-poly1305",
            "password": "password",
            "plugin": "v2ray-plugin",
            "plugin_opts": "host=example.com"
        },
    )
    out = to_singbox_outbound(proxy)
    assert out is not None
    assert out["plugin"] == "v2ray-plugin"
