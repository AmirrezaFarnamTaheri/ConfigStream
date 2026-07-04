# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
from typing import List, Optional, Dict, Any
from ..models import Proxy
from ..security_validator import _safe_log_text, _safe_proxy_ref
from .common import Adapter, _extract_sni
from ..adapters_base import (
    format_singbox_chain_for_loon,
    format_shielded_chain_for_loon,
)

logger = logging.getLogger(__name__)


class LoonAdapter(Adapter):
    """Export to Loon format."""

    def export(
        self,
        proxies: List[Proxy],
        washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        lines = ["# Loon Proxy Export", "[Proxy]"]
        failed_count = 0
        chain_count = 0

        for p in proxies:
            try:
                line = self._format_proxy(p)
                if line:
                    lines.append(line)
            except Exception as e:
                logger.debug(
                    f"Failed to export {_safe_proxy_ref(p)} to Loon: {_safe_log_text(e)}"
                )
                failed_count += 1

        if washed_outbounds:
            for out in washed_outbounds:
                try:
                    if out.get("type") == "wireguard" and out.get("detour"):
                        chain_line = format_singbox_chain_for_loon(
                            out, washed_outbounds
                        )
                        if chain_line:
                            lines.append(chain_line)
                            chain_count += 1
                    if out.get("_is_shielded") and out.get("detour"):
                        # This is the Relay; its detour points at the Shield node.
                        shield_tag = out.get("detour")
                        shield = next(
                            (o for o in washed_outbounds if o.get("tag") == shield_tag),
                            None,
                        )
                        if shield:
                            chain_line = format_shielded_chain_for_loon(out, shield)
                            if chain_line:
                                lines.append(chain_line)
                                chain_count += 1
                except Exception as e:
                    logger.debug(
                        f"Failed to export chain {out.get('tag')} to Loon: {e}"
                    )

        logger.info(
            f"Loon export summary: {len(lines) - 1} proxies, {chain_count} chains (Failures: {failed_count})"
        )
        return "\n".join(lines)

    def _format_proxy(self, p: Proxy) -> str:
        name = p.remarks if p.remarks else f"{p.protocol}_{p.address}"
        name = name.replace("=", "_").replace(",", "_").replace("\n", " ").strip()
        name = "".join(c for c in name if c.isalnum() or c in " -_[]().")

        if p.protocol in ("shadowsocks", "ss"):
            method = p.details.get("method", "chacha20-ietf-poly1305")
            password = p.details.get("password", "")
            return (
                f'{name} = shadowsocks, {p.address}, {p.port}, {method}, "{password}"'
            )

        elif p.protocol == "vmess":
            uuid = p.uuid
            method = p.details.get("method", "chacha20-poly1305")
            sni = _extract_sni(p.details)
            sni_part = f", sni={sni}" if sni else ""
            return (
                f'{name} = vmess, {p.address}, {p.port}, {method}, "{uuid}"{sni_part}'
            )

        elif p.protocol == "trojan":
            password = p.uuid
            sni = _extract_sni(p.details)
            sni_part = f", sni={sni}" if sni else ""
            return f'{name} = trojan, {p.address}, {p.port}, "{password}"{sni_part}'

        return ""
