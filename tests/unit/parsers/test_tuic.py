# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for TUIC v5 protocol parser."""

import pytest
from configstream.parsers.tuic import parse_tuic

UUID = "00000000-0000-4000-8000-000000000001"


def test_parse_tuic_valid_uri() -> None:
    uri = (
        f"tuic://{UUID}:mysecret@1.2.3.4:8443?congestion_control=bbr&alpn=h3#TUIC-Node"
    )
    proxy = parse_tuic(uri)
    assert proxy is not None
    assert proxy.protocol == "tuic"
    assert proxy.address == "1.2.3.4"
    assert proxy.port == 8443
    assert proxy.uuid == UUID
    assert proxy.remarks == "TUIC-Node"
    assert proxy.details.get("congestion_control") == "bbr"


def test_parse_tuic_invalid_uri() -> None:
    assert parse_tuic("tuic://invalid-garbage") is None
    assert parse_tuic("tuic://not-a-uuid:pass@1.2.3.4:8443") is None


def test_parse_tuic_password_required() -> None:
    assert parse_tuic(f"tuic://{UUID}@1.2.3.4:8443") is None


def test_parse_tuic_alpn_is_list() -> None:
    proxy = parse_tuic(f"tuic://{UUID}:pass@1.2.3.4:8443?alpn=h3,spdy/3.1")
    assert proxy is not None
    assert isinstance(proxy.details.get("alpn"), list)
    assert proxy.details["alpn"] == ["h3", "spdy/3.1"]


def test_parse_tuic_default_port() -> None:
    proxy = parse_tuic(f"tuic://{UUID}:pass@1.2.3.4")
    assert proxy is not None
    assert proxy.port == 443


def test_parse_tuic_cc_algo_alias() -> None:
    proxy = parse_tuic(f"tuic://{UUID}:pass@1.2.3.4?congestion_control=bbr")
    assert proxy is not None
    assert proxy.details.get("congestion_control") == "bbr"
    assert proxy.details.get("cc_algo") == "bbr"
