# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the standalone configstream_revival library interface."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
import configstream_revival


def test_library_exports() -> None:
    """Verify that all core components are exported in the library namespace."""
    assert hasattr(configstream_revival, "Proxy")
    assert hasattr(configstream_revival, "ProxyWasher")
    assert hasattr(configstream_revival, "generate_smart_chains")
    assert hasattr(configstream_revival, "PythonTester")
    assert hasattr(configstream_revival, "GoBatchTester")
    assert hasattr(configstream_revival, "test_chain_config")
    assert hasattr(configstream_revival, "to_singbox_outbound")
    assert hasattr(configstream_revival, "to_clash_proxy")
    assert hasattr(configstream_revival, "enrich_outbound_with_evasion")
    assert hasattr(configstream_revival, "StegoPacker")
    assert hasattr(configstream_revival, "generate_stego_assets")
    assert configstream_revival.__version__ == "3.1.0"


def test_proxy_model_usage() -> None:
    """Test that Proxy model instantiated from the standalone library works."""
    proxy = configstream_revival.Proxy(
        config="vmess://example-config-string",
        protocol="vmess",
        address="example.com",
        port=443,
        uuid="uuid-key",
    )
    assert proxy.protocol == "vmess"
    assert proxy.address == "example.com"
    assert proxy.port == 443
    assert proxy.uuid == "uuid-key"


def test_stego_packer_usage(tmp_path) -> None:
    """Test that StegoPacker instantiated from the standalone library works."""
    key = Fernet.generate_key()
    packer = configstream_revival.StegoPacker(key=key)
    assert packer.key == key

    # Test helpers inside stego
    assert packer.cipher is not None
