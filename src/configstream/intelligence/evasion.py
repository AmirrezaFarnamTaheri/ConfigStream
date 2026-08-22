# SPDX-License-Identifier: AGPL-3.0-or-later
"""Evasion configuration helpers with bounded, periodically rotating choices."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TLSFingerprint(Enum):
    CHROME = "chrome"
    FIREFOX = "firefox"
    SAFARI = "safari"
    IOS = "ios"
    ANDROID = "android"
    EDGE = "edge"
    RANDOMIZED = "randomized"


class ALPNProtocol(Enum):
    H2 = "h2"
    HTTP1_1 = "http/1.1"
    HTTP1_0 = "http/1.0"


SAFE_FINGERPRINTS = [
    TLSFingerprint.CHROME,
    TLSFingerprint.FIREFOX,
    TLSFingerprint.SAFARI,
    TLSFingerprint.IOS,
]

SAFE_ALPN_COMBINATIONS = [
    ["h2", "http/1.1"],
    ["http/1.1"],
    ["h2"],
]

# Compatibility sentinel for callers that previously selected sing-box TLS
# fragmentation presets. Current sing-box releases expose no equivalent field.
FRAG_PRESETS: Dict[str, List[Optional[Dict[str, str]]]] = {"none": [None]}


def _rotation_hash(
    proxy_id: str, namespace: str, rotation_seed: Optional[str] = None
) -> int:
    """Return a stable hash within a rotation window, but not forever.

    The default seed changes daily in UTC. Tests and callers that require exact
    reproducibility can pass an explicit seed.
    """
    seed = rotation_seed or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    payload = f"{namespace}\0{seed}\0{proxy_id}".encode("utf-8", errors="strict")
    return int.from_bytes(hashlib.sha256(payload).digest(), "big")


def rotate_tls_fingerprint(
    proxy_id: str,
    enabled: bool = True,
    fingerprint: Optional[str] = None,
    rotation_seed: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if not enabled:
        return None
    if fingerprint:
        normalized = str(fingerprint).strip().lower()
        allowed = {member.value for member in TLSFingerprint}
        if normalized not in allowed:
            logger.warning("Ignoring unsupported TLS fingerprint %r", normalized)
        else:
            return {"enabled": True, "fingerprint": normalized}
    selected = SAFE_FINGERPRINTS[
        _rotation_hash(proxy_id, "tls-fingerprint", rotation_seed)
        % len(SAFE_FINGERPRINTS)
    ]
    return {"enabled": True, "fingerprint": selected.value}


def rotate_alpn(
    proxy_id: str,
    enabled: bool = True,
    alpn: Optional[List[str]] = None,
    rotation_seed: Optional[str] = None,
) -> Optional[List[str]]:
    if not enabled:
        return None
    if alpn:
        normalized = [str(value).strip() for value in alpn if str(value).strip()]
        allowed = {member.value for member in ALPNProtocol}
        invalid = [value for value in normalized if value not in allowed]
        if invalid:
            logger.warning("Ignoring unsupported ALPN values: %s", ", ".join(invalid))
        else:
            return normalized
    selected = SAFE_ALPN_COMBINATIONS[
        _rotation_hash(proxy_id, "alpn", rotation_seed) % len(SAFE_ALPN_COMBINATIONS)
    ]
    return selected.copy()


def add_multiplexing(
    outbound: Dict[str, Any],
    enabled: bool = True,
    padding: bool = True,
    protocol: str = "h2mux",
    max_connections: int = 4,
    min_streams: int = 2,
) -> Dict[str, Any]:
    if not enabled or outbound.get("type", "") not in {
        "vmess",
        "vless",
        "trojan",
        "shadowsocks",
    }:
        return outbound
    if protocol not in {"h2mux", "smux", "yamux"}:
        logger.warning("Unsupported multiplexing protocol %r; using h2mux", protocol)
        protocol = "h2mux"
    outbound["multiplex"] = {
        "enabled": True,
        "padding": bool(padding),
        "protocol": protocol,
        "max_connections": max(1, min(int(max_connections), 64)),
        "min_streams": max(1, min(int(min_streams), 1024)),
    }
    return outbound


def get_fragment_config(
    proxy_id: str,
    enabled: bool = True,
    preset: str = "medium",
    rotation_seed: Optional[str] = None,
) -> None:
    """Deprecated compatibility shim; sing-box TLS fragmentation was removed."""
    return None


def enrich_outbound_with_evasion(
    outbound: Dict[str, Any],
    proxy_id: str,
    enable_utls: bool = True,
    enable_alpn: bool = True,
    enable_fragmentation: bool = False,
    enable_multiplexing: bool = True,
    tls_fingerprint: Optional[str] = None,
    alpn_list: Optional[List[str]] = None,
    fragment_preset: str = "none",
    enable_tfo: bool = False,
    enable_mptcp: bool = False,
    enable_padding: bool = False,
    ech_config: Optional[str] = None,
    rotation_seed: Optional[str] = None,
) -> Dict[str, Any]:
    """Apply supported sing-box evasion fields.

    ``enable_fragmentation``, ``fragment_preset``, and ``enable_padding`` are
    retained as deprecated no-op keywords for callers upgrading from older
    ConfigStream releases. Padding is emitted only by ``multiplex.padding``.
    """
    protocol = outbound.get("type", "")
    tls = outbound.get("tls")

    if enable_utls and protocol in {"vmess", "vless", "trojan", "hysteria2", "tuic"}:
        if isinstance(tls, dict):
            utls_config = rotate_tls_fingerprint(
                proxy_id,
                enabled=True,
                fingerprint=tls_fingerprint,
                rotation_seed=rotation_seed,
            )
            if utls_config:
                tls["utls"] = utls_config

    if (
        enable_alpn
        and protocol in {"vmess", "vless", "trojan"}
        and isinstance(tls, dict)
    ):
        alpn_protocols = rotate_alpn(
            proxy_id,
            enabled=True,
            alpn=alpn_list,
            rotation_seed=rotation_seed,
        )
        if alpn_protocols:
            tls["alpn"] = alpn_protocols

    if ech_config and protocol in {"vmess", "vless", "trojan", "hysteria2", "tuic"}:
        if isinstance(tls, dict):
            tls["ech"] = {"enabled": True, "config": str(ech_config)}

    if (enable_tfo or enable_mptcp) and protocol in {
        "vmess",
        "vless",
        "trojan",
        "shadowsocks",
        "socks",
        "http",
        "hysteria2",
        "tuic",
    }:
        if enable_tfo:
            outbound["tcp_fast_open"] = True
        if enable_mptcp:
            outbound["tcp_multi_path"] = True

    if enable_multiplexing:
        outbound = add_multiplexing(outbound, enabled=True, padding=True)
    return outbound


def preserve_sni_when_using_ip(
    outbound: Dict[str, Any],
    original_hostname: Optional[str] = None,
) -> Dict[str, Any]:
    if not original_hostname:
        return outbound
    tls = outbound.get("tls")
    if isinstance(tls, dict) and not tls.get("server_name"):
        tls["server_name"] = original_hostname

    transport = outbound.get("transport")
    if isinstance(transport, dict):
        if transport.get("type") == "ws":
            headers = transport.get("headers")
            if not isinstance(headers, dict):
                headers = {}
            headers.setdefault("Host", original_hostname)
            transport["headers"] = headers
        elif transport.get("type") == "http":
            transport.setdefault("host", [original_hostname])
    return outbound
