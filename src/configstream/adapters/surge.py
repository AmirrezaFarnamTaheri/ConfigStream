# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
from typing import List, Optional, Dict, Any
from ..models import Proxy
from ..security_validator import _safe_log_text, _safe_proxy_ref
from ..adapters_base import (
    format_singbox_chain_for_surge,
    format_shielded_chain_for_surge,
)
from .common import Adapter, _extract_sni

logger = logging.getLogger(__name__)

class SurgeAdapter(Adapter):
    """Export to Surge 4/5 format."""

    def export(
        self,
        proxies: List[Proxy],
        washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        lines = ["# Surge Policy Export"]
        exported_count = 0
        chain_count = 0
        failed_count = 0

        # 1. Export Standard Proxies
        for p in proxies:
            try:
                line = self._format_proxy(p)
                if line:
                    lines.append(line)
                    exported_count += 1
            except Exception as e:
                logger.debug(
                    f"Failed to export {_safe_proxy_ref(p)} to Surge: {_safe_log_text(e)}"
                )
                failed_count += 1

        # 2. Export Washed/Revived/Shielded Chains
        if washed_outbounds:
            for out in washed_outbounds:
                try:
                    if out.get("type") == "wireguard" and out.get("detour"):
                        chain_line = format_singbox_chain_for_surge(
                            out, washed_outbounds
                        )
                        if chain_line:
                            lines.append(chain_line)
                            chain_count += 1

                    # Handle Shielded Chains (Proxy over WG)
                    if out.get("_is_shielded") and out.get("detour"):
                        # This is the Relay. Detour is the Shield.
                        shield_tag = out.get("detour")
                        shield = next(
                            (o for o in washed_outbounds if o.get("tag") == shield_tag),
                            None,
                        )
                        if shield:
                            chain_line = format_shielded_chain_for_surge(out, shield)
                            if chain_line:
                                lines.append(chain_line)
                                chain_count += 1
                except Exception as e:
                    logger.debug(
                        f"Failed to export chain to Surge: {_safe_log_text(e)}"
                    )
                    failed_count += 1

        logger.info(
            f"Surge export summary: {exported_count} proxies, {chain_count} chains "
            f"(Total Lines: {len(lines)}, Failures: {failed_count})"
        )
        return "\n".join(lines)

    def _format_proxy(self, p: Proxy) -> str:
        name = p.remarks if p.remarks else f"{p.protocol}_{p.address}"
        # Sanitize name: Replace commas with underscores, allow dots
        name = name.replace(",", "_").replace("\n", " ").strip()
        name = "".join(c for c in name if c.isalnum() or c in " -_[]().")

        if p.protocol in ("ss", "shadowsocks"):
            method = p.details.get("method", "chacha20-ietf-poly1305")
            password = p.details.get("password", "")
            return f"{name} = ss, {p.address}, {p.port}, encrypt-method={method}, password={password}"

        elif p.protocol == "vmess":
            uuid = p.uuid
            sni = _extract_sni(p.details)
            sni_part = f", sni={sni}" if sni else ""
            return f"{name} = vmess, {p.address}, {p.port}, username={uuid}{sni_part}"

        elif p.protocol == "vless":
            # Surge 5 supports VLESS
            uuid = p.uuid
            sni = _extract_sni(p.details)
            sni_part = f", sni={sni}" if sni else ""
            return f"{name} = vless, {p.address}, {p.port}, username={uuid}{sni_part}"

        elif p.protocol == "trojan":
            password = p.uuid
            sni = _extract_sni(p.details)
            sni_part = f", sni={sni}" if sni else ""
            return (
                f"{name} = trojan, {p.address}, {p.port}, password={password}{sni_part}"
            )

        elif p.protocol in ("hysteria2", "hy2"):
            password = p.uuid or p.details.get("password", "")
            sni = _extract_sni(p.details)
            sni_part = f", sni={sni}" if sni else ""
            return f"{name} = hysteria2, {p.address}, {p.port}, password={password}{sni_part}"

        elif p.protocol == "tuic":
            # Surge 5.8+ supports TUIC v5
            password = p.uuid or p.details.get("password", "")
            sni = _extract_sni(p.details)
            sni_part = f", sni={sni}" if sni else ""
            return f"{name} = tuic, {p.address}, {p.port}, password={password}{sni_part}, version=5"

        elif p.protocol == "http":
            user = p.uuid
            pwd = p.details.get("password", "")
            auth = f", username={user}, password={pwd}" if user and pwd else ""
            return f"{name} = http, {p.address}, {p.port}{auth}"

        elif p.protocol == "socks5":
            user = p.uuid
            pwd = p.details.get("password", "")
            auth = f", username={user}, password={pwd}" if user and pwd else ""
            return f"{name} = socks5, {p.address}, {p.port}{auth}"

        elif p.protocol == "snell":
            psk = p.details.get("psk", "")
            return f"{name} = snell, {p.address}, {p.port}, psk={psk}"

        return ""
