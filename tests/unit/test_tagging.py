# SPDX-License-Identifier: AGPL-3.0-or-later
from configstream.tagging import ProxyTagger, format_proxy_name
from tests.unit.conftest_helper import create_test_proxy


def test_proxy_tagger():
    pt = ProxyTagger("[{country}] {protocol}")
    p = create_test_proxy(
        source="s",
        address="1.1.1.1",
        port=443,
        protocol="vmess",
        country_code="US",
        is_working=True,
    )

    pt.apply([p])
    assert p.remarks == "[US] VMESS"


def test_format_proxy_name_missing_data():
    p = create_test_proxy(
        source="s", address="1.1.1.1", port=443, protocol="vmess", is_working=True
    )  # No country

    name = format_proxy_name("[{country}] {protocol}", p)
    assert "VMESS" in name  # Protocol is uppercased for display
    assert "[]" not in name


def test_format_proxy_name_full():
    p = create_test_proxy(
        source="s",
        address="1.1.1.1",
        port=443,
        protocol="vmess",
        country_code="US",
        latency=50,
        is_working=True,
    )
    name = format_proxy_name("{country} {latency}ms", p)
    assert name == "US 50ms"
