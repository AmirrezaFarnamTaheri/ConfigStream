# SPDX-License-Identifier: AGPL-3.0-or-later
"""Resolve canonical proxy chains into Sing-box outbound dictionaries."""

from __future__ import annotations

from typing import Any, Dict, List

from .chains import extract_chain_proxies


def chain_outbounds_from_details(details: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Resolve canonical chain details through the Sing-box converter."""
    chain_proxies = extract_chain_proxies(details)
    if details.get("chain"):
        if not isinstance(details["chain"], list) or len(chain_proxies) != len(
            details["chain"]
        ):
            return []
        # Imported here to keep the generic chain model independent of targets.
        from .singbox import to_singbox_outbound

        resolved: List[Dict[str, Any]] = []
        for hop in chain_proxies:
            outbound = to_singbox_outbound(hop)
            if isinstance(outbound, dict):
                resolved.append(outbound)
            else:
                return []
        return resolved

    chain_outbounds = details.get("chain_outbounds")
    if isinstance(chain_outbounds, list) and chain_outbounds:
        return (
            list(chain_outbounds)
            if all(isinstance(item, dict) for item in chain_outbounds)
            else []
        )
    return []


chain_obs_from_details = chain_outbounds_from_details
