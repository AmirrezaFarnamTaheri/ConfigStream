# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Evasion Intelligence: Advanced anti-censorship features.

This module provides TLS fingerprint rotation, ALPN rotation, padding strategies,
and other evasion techniques to bypass DPI and censorship.
"""

import hashlib
import logging
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class TLSFingerprint(Enum):
    """Supported TLS fingerprints."""

    CHROME = "chrome"
    FIREFOX = "firefox"
    SAFARI = "safari"
    IOS = "ios"
    ANDROID = "android"
    EDGE = "edge"
    RANDOMIZED = "randomized"


class ALPNProtocol(Enum):
    """Supported ALPN protocols."""

    H2 = "h2"
    HTTP1_1 = "http/1.1"
    HTTP1_0 = "http/1.0"


# Safe fingerprint set for rotation
SAFE_FINGERPRINTS = [
    TLSFingerprint.CHROME,
    TLSFingerprint.FIREFOX,
    TLSFingerprint.SAFARI,
    TLSFingerprint.IOS,
]

# Safe ALPN combinations
SAFE_ALPN_COMBINATIONS = [
    ["h2", "http/1.1"],
    ["http/1.1"],
    ["h2"],
]


def rotate_tls_fingerprint(
    proxy_id: str,
    enabled: bool = True,
    fingerprint: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Rotate TLS fingerprint for a proxy.

    Args:
        proxy_id: Unique proxy identifier for deterministic rotation
        enabled: Whether to enable uTLS
        fingerprint: Specific fingerprint to use, or None for rotation

    Returns:
        uTLS configuration dict or None
    """
    if not enabled:
        return None

    if fingerprint:
        # Use specified fingerprint
        return {"enabled": True, "fingerprint": fingerprint}

    # Deterministic rotation based on proxy ID
    hash_val = int(hashlib.sha256(proxy_id.encode()).hexdigest(), 16)
    selected = SAFE_FINGERPRINTS[hash_val % len(SAFE_FINGERPRINTS)]
    return {"enabled": True, "fingerprint": selected.value}


def rotate_alpn(
    proxy_id: str,
    enabled: bool = True,
    alpn: Optional[List[str]] = None,
) -> Optional[List[str]]:
    """
    Rotate ALPN protocols for a proxy.

    Args:
        proxy_id: Unique proxy identifier for deterministic rotation
        enabled: Whether to enable ALPN rotation
        alpn: Specific ALPN list to use, or None for rotation

    Returns:
        ALPN list or None
    """
    if not enabled:
        return None

    if alpn:
        return alpn

    # Deterministic rotation based on proxy ID
    hash_val = int(hashlib.sha256(proxy_id.encode()).hexdigest(), 16)
    selected = SAFE_ALPN_COMBINATIONS[hash_val % len(SAFE_ALPN_COMBINATIONS)]
    return selected.copy()


def add_multiplexing(
    outbound: Dict[str, Any],
    enabled: bool = True,
    padding: bool = True,
    protocol: str = "h2mux",
    max_connections: int = 4,
    min_streams: int = 2,
) -> Dict[str, Any]:
    """
    Add multiplexing with padding to an outbound config.

    Args:
        outbound: Sing-box outbound configuration
        enabled: Whether to enable multiplexing
        padding: Whether to enable padding (adds noise to packet sizes)
        protocol: Multiplexing protocol (h2mux, smux)
        max_connections: Maximum concurrent connections
        min_streams: Minimum streams per connection

    Returns:
        Updated outbound config
    """
    if not enabled:
        return outbound

    # Only apply to protocols that support multiplexing
    protocol_type = outbound.get("type", "")
    if protocol_type not in ["vmess", "vless", "trojan", "shadowsocks"]:
        return outbound

    outbound["multiplex"] = {
        "enabled": True,
        "padding": padding,
        "protocol": protocol,
        "max_connections": max_connections,
        "min_streams": min_streams,
    }

    return outbound


# Fragmentation presets from cfray
FRAG_PRESETS: Dict[str, List[Optional[Dict[str, str]]]] = {
    "none": [None],
    "light": [
        {"packets": "tlshello", "length": "100-200", "interval": "10-20"},
    ],
    "medium": [
        {"packets": "tlshello", "length": "50-100", "interval": "10-20"},
        {"packets": "tlshello", "length": "100-200", "interval": "20-40"},
    ],
    "heavy": [
        {"packets": "tlshello", "length": "10-50", "interval": "5-10"},
        {"packets": "tlshello", "length": "50-100", "interval": "10-30"},
        {"packets": "tlshello", "length": "100-300", "interval": "20-50"},
    ],
    "all": [
        None,
        {"packets": "tlshello", "length": "100-200", "interval": "10-20"},
        {"packets": "tlshello", "length": "50-100", "interval": "10-30"},
        {"packets": "tlshello", "length": "10-50", "interval": "5-10"},
    ],
}


def get_fragment_config(
    proxy_id: str,
    enabled: bool = True,
    preset: str = "medium",
) -> Optional[Dict[str, Any]]:
    """
    Select a fragmentation configuration from presets deterministically based on proxy ID.
    """
    if not enabled or preset == "none":
        return None

    choices = FRAG_PRESETS.get(preset)
    if not choices:
        choices = FRAG_PRESETS["medium"]  # Fallback

    valid_choices = [c for c in choices if c is not None]
    if not valid_choices:
        return None

    # Deterministic selection based on proxy ID
    hash_val = int(hashlib.sha256(proxy_id.encode()).hexdigest(), 16)
    selected = valid_choices[hash_val % len(valid_choices)]
    return selected.copy()


def enrich_outbound_with_evasion(
    outbound: Dict[str, Any],
    proxy_id: str,
    enable_utls: bool = True,
    enable_alpn: bool = True,
    enable_fragmentation: bool = True,
    enable_multiplexing: bool = True,
    tls_fingerprint: Optional[str] = None,
    alpn_list: Optional[List[str]] = None,
    fragment_preset: str = "medium",
) -> Dict[str, Any]:
    """
    Enrich an outbound config with evasion features.

    Args:
        outbound: Sing-box outbound configuration
        proxy_id: Unique proxy identifier
        enable_utls: Enable TLS fingerprint rotation
        enable_alpn: Enable ALPN rotation
        enable_fragmentation: Enable TLS fragmentation
        enable_multiplexing: Enable multiplexing with padding
        tls_fingerprint: Specific fingerprint to use (optional)
        alpn_list: Specific ALPN list to use (optional)
        fragment_preset: Specific fragmentation preset to use (optional, defaults to "medium")

    Returns:
        Enriched outbound config
    """
    protocol = outbound.get("type", "")

    # Apply uTLS fingerprint rotation
    if enable_utls and protocol in ["vmess", "vless", "trojan", "hysteria2", "tuic"]:
        if "tls" in outbound and isinstance(outbound["tls"], dict):
            utls_config = rotate_tls_fingerprint(
                proxy_id, enabled=True, fingerprint=tls_fingerprint
            )
            if utls_config:
                outbound["tls"]["utls"] = utls_config

    # Apply ALPN rotation
    if enable_alpn and protocol in ["vmess", "vless", "trojan"]:
        if "tls" in outbound and isinstance(outbound["tls"], dict):
            alpn_protocols = rotate_alpn(proxy_id, enabled=True, alpn=alpn_list)
            if alpn_protocols:
                outbound["tls"]["alpn"] = alpn_protocols

    # Apply TLS fragmentation
    if enable_fragmentation and protocol in ["vmess", "vless", "trojan"]:
        # Do not fragment XTLS-Vision or Reality
        is_reality = False
        if "tls" in outbound and isinstance(outbound["tls"], dict):
            if outbound["tls"].get("reality", {}).get("enabled"):
                is_reality = True
        is_vision = outbound.get("flow", "").startswith("xtls-rprx-vision")

        if not is_reality and not is_vision:
            frag_cfg = get_fragment_config(proxy_id, enabled=True, preset=fragment_preset)
            if frag_cfg:
                dial = outbound.get("dial", {})
                if not isinstance(dial, dict):
                    dial = {}
                dial["fragment"] = {
                    "enabled": True,
                    **frag_cfg
                }
                outbound["dial"] = dial

    # Apply multiplexing with padding
    if enable_multiplexing:
        outbound = add_multiplexing(outbound, enabled=True, padding=True)

    return outbound


def preserve_sni_when_using_ip(
    outbound: Dict[str, Any],
    original_hostname: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Preserve SNI/Host when using resolved IP address.

    Args:
        outbound: Sing-box outbound configuration
        original_hostname: Original hostname to preserve in SNI

    Returns:
        Updated outbound config with SNI preserved
    """
    if not original_hostname:
        return outbound

    # Preserve SNI in TLS config
    if "tls" in outbound and isinstance(outbound["tls"], dict):
        if not outbound["tls"].get("server_name"):
            outbound["tls"]["server_name"] = original_hostname

    # Preserve Host header in transport
    if "transport" in outbound:
        transport = outbound["transport"]
        if isinstance(transport, dict):
            if transport.get("type") == "ws":
                headers = transport.get("headers", {})
                if "Host" not in headers:
                    headers["Host"] = original_hostname
                    transport["headers"] = headers
            elif transport.get("type") == "http":
                if "host" not in transport:
                    transport["host"] = [original_hostname]

    return outbound
