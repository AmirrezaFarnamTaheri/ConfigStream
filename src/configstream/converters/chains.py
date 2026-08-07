# SPDX-License-Identifier: AGPL-3.0-or-later
"""Helpers for canonical chain handling across converter targets."""

from __future__ import annotations
import logging

import copy
from typing import Any, Dict, List, Optional

from ..models import Proxy


def _proxy_from_dict(data: Dict[str, Any]) -> Optional[Proxy]:
    """Best-effort Proxy reconstruction from dictionary payload."""
    try:
        return Proxy(**data)
    except (TypeError, ValueError):
        logger = logging.getLogger(__name__)
        logger.debug("Skipped invalid canonical chain proxy payload")
        return None


def extract_chain_proxies(details: Dict[str, Any]) -> List[Proxy]:
    """
    Extract canonical chain proxies from proxy details.

    Supported formats:
    - ``details["chain"]`` as list[Proxy] or list[dict]
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


def chain_obs_from_details(details: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Compatibility shim for the resolver now owned by ``chain_outbounds``."""
    from .chain_outbounds import chain_outbounds_from_details

    return chain_outbounds_from_details(details)


chain_outbounds_from_details = chain_obs_from_details


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

    # Also persist the resolved sing-box outbounds so downstream consumers
    # (Clash generator, DNS-safe rewrite tests) can read them directly.
    details["chain_outbounds"] = sanitized
