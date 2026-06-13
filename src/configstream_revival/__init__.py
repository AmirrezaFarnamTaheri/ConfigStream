# SPDX-License-Identifier: AGPL-3.0-or-later
"""
ConfigStream Revival & Tester Engine Standalone Library.

This library exports the core anti-censorship IP of ConfigStream:
1. Proxy Revival (Washing) via WARP/Vwarp chaining.
2. Triple-Engine testing (Go sidecar, Python fallback, WASM/browser).
3. Configuration converters (Sing-box, Clash outbounds).
4. Evasion & Steganography helpers.
"""

from __future__ import annotations

__version__ = "3.1.0"

# Core Models
from configstream.models import Proxy

# Revival (Washing) & Chaining Engine
from configstream.intelligence.washer.core import ProxyWasher
from configstream.intelligence.chaining import generate_smart_chains

# Testing Stack
from configstream.testers.python import PythonTester
from configstream.testers.go import GoBatchTester
from configstream.testers.lab_chain_tester import test_chain_config

# Converters & Evasion
from configstream.converters.singbox import to_singbox_outbound
from configstream.converters.clash import to_clash_proxy
from configstream.intelligence.evasion import enrich_outbound_with_evasion

# Steganography Obfuscator
from configstream.stego import StegoPacker, generate_stego_assets

__all__ = [
    "Proxy",
    "ProxyWasher",
    "generate_smart_chains",
    "PythonTester",
    "GoBatchTester",
    "test_chain_config",
    "to_singbox_outbound",
    "to_clash_proxy",
    "enrich_outbound_with_evasion",
    "StegoPacker",
    "generate_stego_assets",
]
