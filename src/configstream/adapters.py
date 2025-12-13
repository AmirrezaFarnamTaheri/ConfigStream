"""
Client Adapters for exporting proxies to various formats.
Supports Surge, Loon, Quantumult X, Shadowrocket, and SIP008.
"""

import abc
import json
import logging
import base64
import urllib.parse
from typing import List, Optional, Dict, Any
from .models import Proxy
from .adapters_base import format_singbox_chain_for_surge, format_singbox_chain_for_loon

logger = logging.getLogger(__name__)


class Adapter(abc.ABC):
    """Base class for proxy adapters."""

    @abc.abstractmethod
    def export(
        self,
        proxies: List[Proxy],
        washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Export a list of proxies to the adapter's format."""
        pass


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
                logger.debug(f"Failed to export {p.protocol} to Surge: {e}")
                failed_count += 1

        # 2. Export Washed Proxies
        if washed_outbounds:
            for out in washed_outbounds:
                try:
                    if (
                        out.get("type") == "wireguard"
                        and out.get("tag", "").startswith("🛡️ Secure")
                        and out.get("detour")
                    ):
                        chain_line = format_singbox_chain_for_surge(
                            out, washed_outbounds
                        )
                        if chain_line:
                            lines.append(chain_line)
                            chain_count += 1
                except Exception as e:
                    logger.debug(f"Failed to export chain to Surge: {e}")
                    failed_count += 1

        logger.info(
            f"Surge export summary: {exported_count} proxies, {chain_count} chains "
            f"(Total Lines: {len(lines)}, Failures: {failed_count})"
        )
        return "\n".join(lines)

    def _format_proxy(self, p: Proxy) -> str:
        name = p.remarks if p.remarks else f"{p.protocol}_{p.address}"
        name = name.replace(",", "_").strip()

        if p.protocol in ("ss", "shadowsocks"):
            method = p.details.get("method", "chacha20-ietf-poly1305")
            password = p.details.get("password", "")
            return f"{name} = ss, {p.address}, {p.port}, encrypt-method={method}, password={password}"

        elif p.protocol == "vmess":
            uuid = p.uuid
            return f"{name} = vmess, {p.address}, {p.port}, username={uuid}"

        elif p.protocol == "vless":
            # Surge 5 supports VLESS
            uuid = p.uuid
            return f"{name} = vless, {p.address}, {p.port}, username={uuid}"

        elif p.protocol == "trojan":
            password = p.uuid
            return f"{name} = trojan, {p.address}, {p.port}, password={password}"

        elif p.protocol in ("hysteria2", "hy2"):
            password = p.uuid or p.details.get("password", "")
            sni = p.details.get("sni", "")
            return f"{name} = hysteria2, {p.address}, {p.port}, password={password}, sni={sni}"

        elif p.protocol == "tuic":
            # Surge 5.8+ supports TUIC v5
            password = p.uuid or p.details.get("password", "")
            sni = p.details.get("sni", "")
            return f"{name} = tuic, {p.address}, {p.port}, password={password}, sni={sni}, version=5"

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


class LoonAdapter(Adapter):
    """Export to Loon format."""

    def export(
        self,
        proxies: List[Proxy],
        washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        lines = ["# Loon Proxy Export"]

        # 1. Export Standard Proxies
        for p in proxies:
            try:
                line = self._format_proxy(p)
                if line:
                    lines.append(line)
            except Exception as e:
                logger.debug(f"Failed to export {p.protocol} to Loon: {e}")

        # 2. Export Washed Proxies
        chain_count = 0
        if washed_outbounds:
            for out in washed_outbounds:
                try:
                    if (
                        out.get("type") == "wireguard"
                        and out.get("tag", "").startswith("🛡️ Secure")
                        and out.get("detour")
                    ):
                        chain_line = format_singbox_chain_for_loon(
                            out, washed_outbounds
                        )
                        if chain_line:
                            lines.append(chain_line)
                            chain_count += 1
                except Exception as e:
                    logger.debug(f"Failed to export chain to Loon: {e}")

        logger.info(
            f"Loon export summary: {len(lines) - 1 - chain_count} proxies, {chain_count} chains"
        )
        return "\n".join(lines)

    def _format_proxy(self, p: Proxy) -> str:
        name = p.remarks if p.remarks else f"{p.protocol}_{p.address}"
        name = name.replace("=", "_").replace(",", "_").strip()

        if p.protocol == "shadowsocks":
            method = p.details.get("method", "chacha20-ietf-poly1305")
            password = p.details.get("password", "")
            return f'{name} = shadowsocks, {p.address}, {p.port}, {method}, "{password}"'

        elif p.protocol == "vmess":
            uuid = p.uuid
            method = p.details.get("method", "auto")
            return f'{name} = vmess, {p.address}, {p.port}, {method}, "{uuid}"'

        elif p.protocol == "trojan":
            password = p.uuid
            return f'{name} = trojan, {p.address}, {p.port}, "{password}"'

        elif p.protocol == "vless":
            # Loon VLESS format: name = vless, host, port, uuid
            return f'{name} = vless, {p.address}, {p.port}, "{p.uuid}"'

        elif p.protocol in ("hysteria2", "hy2"):
            # Loon Hysteria2
            sni = p.details.get("sni", "")
            return f'{name} = hysteria2, {p.address}, {p.port}, password="{p.uuid}", sni={sni}'

        elif p.protocol == "tuic":
            # Loon TUIC
            sni = p.details.get("sni", "")
            return f'{name} = tuic, {p.address}, {p.port}, password="{p.uuid}", sni={sni}'

        elif p.protocol == "wireguard":
            # Loon WireGuard (standard)
            # name = wireguard, ip, port, private-key=..., public-key=...
            priv = p.details.get("private_key", "")
            pub = p.details.get("peer_public_key", "")
            return f'{name} = wireguard, {p.address}, {p.port}, private-key="{priv}", peer-public-key="{pub}"'

        return ""


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
                logger.debug(f"Failed to export {p.protocol} to QuantumultX: {e}")
                failed_count += 1

        logger.info(
            f"Quantumult X export summary: {len(lines)} proxies (Failures: {failed_count})"
        )
        return "\n".join(lines)

    def _format_proxy(self, p: Proxy) -> str:
        name = p.remarks if p.remarks else f"{p.protocol}_{p.address}"
        name = name.replace("=", "").replace(",", "").strip()

        if p.protocol == "shadowsocks":
            method = p.details.get("method", "chacha20-ietf-poly1305")
            password = p.details.get("password", "")
            return f"shadowsocks={name}: {p.address}, {p.port}, method={method}, password={password}"

        elif p.protocol == "vmess":
            uuid = p.uuid
            method = p.details.get("method", "chacha20-poly1305")
            return f"vmess={name}: {p.address}, {p.port}, method={method}, password={uuid}"

        elif p.protocol == "trojan":
            password = p.uuid
            return f"trojan={name}: {p.address}, {p.port}, password={password}, over-tls=true, tls-host={p.details.get('sni', '')}"

        elif p.protocol == "vless":
            # QX VLESS format: vless=name: host, port, method=none, uuid=...
            # Note: QX supports VLESS but it requires the 'vless' module/keyword
            return f"vless={name}: {p.address}, {p.port}, method=none, uuid={p.uuid}"

        elif p.protocol == "http":
            user = p.uuid
            pwd = p.details.get("password", "")
            return f"http={name}: {p.address}, {p.port}, username={user}, password={pwd}"

        return ""


class ShadowrocketAdapter(Adapter):
    """Export to Shadowrocket format (Base64 encoded links or plain URI list)."""

    def export(
        self,
        proxies: List[Proxy],
        washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        lines = []
        reconstructed_count = 0
        for p in proxies:
            # Shadowrocket supports standard URIs natively
            if p.config and "://" in p.config:
                lines.append(p.config)
                continue

            # Fallback to reconstruction
            try:
                uri = self._reconstruct_uri(p)
                if uri:
                    lines.append(uri)
                    reconstructed_count += 1
            except Exception as e:
                logger.debug(f"Failed to reconstruct URI for {p.protocol}: {e}")

        logger.info(
            f"Shadowrocket export summary: {len(lines)} links (Reconstructed: {reconstructed_count})"
        )
        return "\n".join(lines)

    def _reconstruct_uri(self, p: Proxy) -> str:
        """Reconstruct URI with full protocol support."""
        name = urllib.parse.quote(p.remarks or "ConfigStream")

        if p.protocol in ("ss", "shadowsocks"):
            method = p.details.get("method", "chacha20-ietf-poly1305")
            password = p.details.get("password", "")
            userpass = f"{method}:{password}"
            b64_auth = base64.urlsafe_b64encode(userpass.encode()).decode().rstrip("=")
            return f"ss://{b64_auth}@{p.address}:{p.port}#{name}"

        elif p.protocol == "trojan":
            sni = p.details.get("sni", "")
            return f"trojan://{p.uuid}@{p.address}:{p.port}?peer={sni}&sni={sni}#{name}"

        elif p.protocol == "vmess":
            # Simplified VMess reconstruction (often better to use original if available)
            # This is a basic fallback
            import json
            v_obj = {
                "v": "2",
                "ps": p.remarks or "ConfigStream",
                "add": p.address,
                "port": str(p.port),
                "id": p.uuid,
                "aid": "0",
                "net": p.details.get("net", "tcp"),
                "type": "none",
                "host": p.details.get("host", ""),
                "tls": p.details.get("tls", ""),
            }
            return "vmess://" + base64.b64encode(json.dumps(v_obj).encode()).decode()

        elif p.protocol == "vless":
            # vless://uuid@host:port?params#name
            security = p.details.get("security", "tls")
            sni = p.details.get("sni", "")
            net = p.details.get("net", "tcp")
            params = f"security={security}&sni={sni}&type={net}"
            return f"vless://{p.uuid}@{p.address}:{p.port}?{params}#{name}"

        elif p.protocol in ("hysteria2", "hy2"):
            # hysteria2://password@host:port?sni=...#name
            sni = p.details.get("sni", "")
            return f"hysteria2://{p.uuid}@{p.address}:{p.port}?sni={sni}#{name}"

        elif p.protocol == "tuic":
            # tuic://uuid:password@host:port?sni=...#name
            # TUIC V5 usually just uses UUID as auth or uuid:pass
            sni = p.details.get("sni", "")
            password = p.details.get("password", "")
            return f"tuic://{p.uuid}:{password}@{p.address}:{p.port}?sni={sni}#{name}"

        return ""


class SIP008Adapter(Adapter):
    """Export to SIP008 JSON format."""

    def export(
        self,
        proxies: List[Proxy],
        washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        servers = []
        for p in proxies:
            if p.protocol == "shadowsocks":
                server = {
                    "server": p.address,
                    "server_port": p.port,
                    "password": p.details.get("password", ""),
                    "method": p.details.get("method", "chacha20-ietf-poly1305"),
                    "remarks": p.remarks,
                }
                servers.append(server)

        logger.info(f"SIP008 export summary: {len(servers)} Shadowsocks servers")
        return json.dumps(
            {"version": 1, "servers": servers, "bytes_used": 0, "bytes_remaining": 0},
            indent=2,
        )


def get_adapter(format_name: str) -> Adapter:
    f = format_name.lower()
    if f == "surge":
        return SurgeAdapter()
    elif f == "loon":
        return LoonAdapter()
    elif f in ["qx", "quantumultx"]:
        return QuantumultXAdapter()
    elif f == "sip008":
        return SIP008Adapter()
    elif f == "shadowrocket":
        return ShadowrocketAdapter()
    else:
        raise ValueError(f"Unknown format: {format_name}")
