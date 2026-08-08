# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
from typing import List, Optional, Dict, Any
from ..models import Proxy
from ..security_validator import safe_log_text, _safe_proxy_ref
from .common import Adapter, _extract_sni

logger = logging.getLogger(__name__)


class QuantumultXAdapter(Adapter):
    """Export to Quantumult X format."""

    def export(
        self,
        proxies: List[Proxy],
        washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        lines = []
        failed_count = 0
        for p in proxies:
            try:
                line = self._format_proxy(p)
                if line:
                    lines.append(line)
            except Exception as e:
                logger.debug(
                    f"Failed to export {_safe_proxy_ref(p)} to QuantumultX: {safe_log_text(e)}"
                )
                failed_count += 1

        logger.info(
            f"Quantumult X export summary: {len(lines)} proxies (Failures: {failed_count})"
        )
        return "\n".join(lines)

    def _format_proxy(self, p: Proxy) -> str:
        name = p.remarks if p.remarks else f"{p.protocol}_{p.address}"
        name = name.replace("=", "").replace(",", "").strip()

        if p.protocol in ("shadowsocks", "ss"):
            method = p.details.get("method", "chacha20-ietf-poly1305")
            password = p.details.get("password", "")
            return f"shadowsocks={name}: {p.address}, {p.port}, method={method}, password={password}"

        elif p.protocol == "vmess":
            uuid = p.uuid
            method = p.details.get("method", "chacha20-poly1305")
            sni = _extract_sni(p.details)
            sni_part = f", sni={sni}" if sni else ""
            return f"vmess={name}: {p.address}, {p.port}, method={method}, password={uuid}{sni_part}"

        elif p.protocol == "trojan":
            password = p.uuid
            sni = _extract_sni(p.details)
            sni_part = f", tls-host={sni}" if sni else ""
            return f"trojan={name}: {p.address}, {p.port}, password={password}, over-tls=true{sni_part}"

        elif p.protocol == "vless":
            sni = _extract_sni(p.details)
            sni_part = f", sni={sni}" if sni else ""
            return f"vless={name}: {p.address}, {p.port}, method=none, uuid={p.uuid}{sni_part}"

        elif p.protocol == "http":
            user = p.uuid
            pwd = p.details.get("password", "")
            return (
                f"http={name}: {p.address}, {p.port}, username={user}, password={pwd}"
            )

        return ""
