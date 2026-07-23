# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for Hysteria3 protocol parser."""
import pytest
from configstream.parsers.hysteria3 import parse_hysteria3

def test_parse_hysteria3_valid_uri():
    uri = "hy3://secretpass@5.6.7.8:443?obfs=salamander&obfs-password=pass123#Hy3-Node"
    proxy = parse_hysteria3(uri)
    assert proxy is not None
    assert proxy.protocol == "hysteria3"
    assert proxy.address == "5.6.7.8"
    assert proxy.port == 443
    assert proxy.remarks == "Hy3-Node"
    assert proxy.details.get("obfs") == "salamander"

def test_parse_hysteria3_invalid_uri():
    assert parse_hysteria3("hy3://invalid-garbage") is None
