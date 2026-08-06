# SPDX-License-Identifier: AGPL-3.0-or-later
"""Resolve canonical proxy chains into Sing-box outbound dictionaries."""

from __future__ import annotations

from typing import Any, Dict, List

from .chains import extract_chain_proxies


def chain_outbounds_from_details(details: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Resolve canonical chain details through the Sing-box converter."""
    chain_proxies = extract_chain_proxies(details)
    if chain_proxies:
        # Imported here to keep the generic chain model independent of targets.
        from .singbox import to_singbox_outbound

        resolved: List[Dict[str, Any]] = []
        for hop in chain_proxies:
            outbound = to_singbox_outbound(hop)
            if isinstance(outbound, dict):
                resolved.append(outbound)
        return resolved

    chain_outbounds = details.get("chain_outbounds")
    if isinstance(chain_outbounds, list) and chain_outbounds:
        return [item for item in chain_outbounds if isinstance(item, dict)]
    return []


chain_obs_from_details = chain_outbounds_from_details
