# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from configstream.models import Proxy
from configstream.parsers.normalization import normalize_proxy_details


def test_normalize_sni():
    p = Proxy(
        config="test",
        protocol="vmess",
        address="1.1.1.1",
        port=443,
        details={"sni": "example.com"},
    )
    normalize_proxy_details(p)
    assert p.details["sni"] == "example.com"

    # Priority check: sni > peer > host
    p = Proxy(
        config="test",
        protocol="vmess",
        address="1.1.1.1",
        port=443,
        details={"peer": "peer.com", "host": "host.com"},
    )
    normalize_proxy_details(p)
    assert p.details["sni"] == "peer.com"

    p = Proxy(
        config="test",
        protocol="vmess",
        address="1.1.1.1",
        port=443,
        details={"host": "host.com"},
    )
    normalize_proxy_details(p)
    assert p.details["sni"] == "host.com"


def test_normalize_vmess_headers():
    p = Proxy(
        config="test",
        protocol="vmess",
        address="1.1.1.1",
        port=443,
        details={"headers": {"Host": "header.com"}},
    )
    normalize_proxy_details(p)
    assert p.details["sni"] == "header.com"


def test_normalize_shadowsocks_plugin():
    p = Proxy(
        config="test",
        protocol="shadowsocks",
        address="1.1.1.1",
        port=443,
        details={"plugin": "obfs-local;obfs=http;obfs-host=plugin.com"},
    )
    normalize_proxy_details(p)
    assert p.details["sni"] == "plugin.com"


def test_normalize_path():
    p = Proxy(
        config="test",
        protocol="ws",
        address="1.1.1.1",
        port=443,
        details={"path": "/ws"},
    )
    normalize_proxy_details(p)
    assert p.details["path"] == "/ws"

    p = Proxy(
        config="test",
        protocol="ws",
        address="1.1.1.1",
        port=443,
        details={"serviceName": "/grpc"},
    )
    normalize_proxy_details(p)
    assert p.details["path"] == "/grpc"


def test_normalize_alpn():
    p = Proxy(
        config="test",
        protocol="vless",
        address="1.1.1.1",
        port=443,
        details={"alpn": "h2,http/1.1"},
    )
    normalize_proxy_details(p)
    assert p.details["alpn"] == ["h2", "http/1.1"]

    p = Proxy(
        config="test",
        protocol="vless",
        address="1.1.1.1",
        port=443,
        details={"alpn": ["h3"]},
    )
    normalize_proxy_details(p)
    assert p.details["alpn"] == ["h3"]
