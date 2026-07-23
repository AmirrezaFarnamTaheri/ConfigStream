# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for TUIC v5 protocol parser."""
import pytest
from configstream.parsers.tuic import parse_tuic

def test_parse_tuic_valid_uri():
    uri = "tuic://00000000-0000-0000-0000-000000000001:mysecret@1.2.3.4:8443?congestion_control=bbr&alpn=h3#TUIC-Node"
    proxy = parse_tuic(uri)
    assert proxy is not None
    assert proxy.protocol == "tuic"
    assert proxy.address == "1.2.3.4"
    assert proxy.port == 8443
    assert proxy.uuid == "00000000-0000-0000-0000-000000000001"
    assert proxy.remarks == "TUIC-Node"
    assert proxy.details.get("congestion_control") == "bbr"

def test_parse_tuic_invalid_uri():
    assert parse_tuic("tuic://invalid-garbage") is None
