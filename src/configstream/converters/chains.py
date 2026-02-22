# SPDX-License-Identifier: AGPL-3.0-or-later
"""Helpers for canonical chain handling across converter targets."""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from ..models import Proxy


def _proxy_from_dict(data: Dict[str, Any]) -> Optional[Proxy]:
    """Best-effort Proxy reconstruction from dictionary payload."""
    try:
        return Proxy(**data)
    except Exception:  # nosec
        return None


def extract_chain_proxies(details: Dict[str, Any]) -> List[Proxy]:
    """
    Extract canonical chain proxies from proxy details.

    Supported formats:
    - ``details["chain"]`` as list[Proxy] or list[dict]
    - legacy ``details["chain_outbounds"]`` is ignored here (handled elsewhere)
    """
    chain = details.get("chain")
    if not isinstance(chain, list):
        return []

    proxies: List[Proxy] = []
    for item in chain:
        if isinstance(item, Proxy):
            proxies.append(item)
            continue
        if isinstance(item, dict):
            proxy = _proxy_from_dict(item)
            if proxy:
                proxies.append(proxy)
    return proxies


def chain_outbounds_from_details(details: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Resolve sing-box outbounds from canonical or legacy chain details.

    Preference order:
    1. canonical ``details["chain"]`` converted via ``to_singbox_outbound``
    2. legacy ``details["chain_outbounds"]``
    """
    chain_proxies = extract_chain_proxies(details)
    if chain_proxies:
        from .singbox import to_singbox_outbound

        resolved: List[Dict[str, Any]] = []
        for hop in chain_proxies:
            out = to_singbox_outbound(hop)
            if isinstance(out, dict):
                resolved.append(out)
        if resolved:
            return resolved

    legacy = details.get("chain_outbounds")
    if isinstance(legacy, list):
        return [copy.deepcopy(o) for o in legacy if isinstance(o, dict)]
    return []


def _safe_port(value: Any) -> Optional[int]:
    try:
        port = int(value)
    except (TypeError, ValueError):
        return None
    if 1 <= port <= 65535:
        return port
    return None


def _apply_outbound_to_proxy(hop: Proxy, outbound: Dict[str, Any]) -> Proxy:
    updated = hop.model_copy(deep=True)
    server = outbound.get("server")
    if isinstance(server, str) and server.strip():
        updated.address = server.strip()
    port = _safe_port(outbound.get("server_port"))
    if port is not None:
        updated.port = port

    details = dict(updated.details or {})
    tag = outbound.get("tag")
    if isinstance(tag, str) and tag.strip():
        details["tag"] = tag.strip()
    detour = outbound.get("detour")
    if isinstance(detour, str) and detour.strip():
        details["detour"] = detour.strip()
    tls = outbound.get("tls")
    if isinstance(tls, dict):
        server_name = tls.get("server_name")
        if (
            isinstance(server_name, str)
            and server_name.strip()
            and not details.get("sni")
        ):
            details["sni"] = server_name.strip()
    updated.details = details
    return updated


def _apply_outbound_to_dict(
    hop: Dict[str, Any], outbound: Dict[str, Any]
) -> Dict[str, Any]:
    updated = copy.deepcopy(hop)
    server = outbound.get("server")
    if isinstance(server, str) and server.strip():
        updated["address"] = server.strip()
    port = _safe_port(outbound.get("server_port"))
    if port is not None:
        updated["port"] = port

    details = updated.get("details")
    if not isinstance(details, dict):
        details = {}
    else:
        details = dict(details)

    tag = outbound.get("tag")
    if isinstance(tag, str) and tag.strip():
        details["tag"] = tag.strip()
    detour = outbound.get("detour")
    if isinstance(detour, str) and detour.strip():
        details["detour"] = detour.strip()
    tls = outbound.get("tls")
    if isinstance(tls, dict):
        server_name = tls.get("server_name")
        if (
            isinstance(server_name, str)
            and server_name.strip()
            and not details.get("sni")
        ):
            details["sni"] = server_name.strip()

    if details:
        updated["details"] = details
    return updated


def update_chain_details(
    details: Dict[str, Any], outbounds: List[Dict[str, Any]]
) -> None:
    """
    Persist rewritten chain outbounds back into details.

    - Updates canonical ``details["chain"]`` hop address/port/tag/detour when present.
    - Keeps ``details["chain_outbounds"]`` for backward compatibility.
    """
    sanitized = [copy.deepcopy(ob) for ob in outbounds if isinstance(ob, dict)]
    if not sanitized:
        return

    chain = details.get("chain")
    if isinstance(chain, list):
        rewritten_chain: List[Any] = []
        for idx, hop in enumerate(chain):
            outbound = sanitized[idx] if idx < len(sanitized) else None
            if outbound is None:
                rewritten_chain.append(hop)
                continue
            if isinstance(hop, Proxy):
                rewritten_chain.append(_apply_outbound_to_proxy(hop, outbound))
            elif isinstance(hop, dict):
                rewritten_chain.append(_apply_outbound_to_dict(hop, outbound))
            else:
                rewritten_chain.append(hop)
        details["chain"] = rewritten_chain

    details["chain_outbounds"] = sanitized
