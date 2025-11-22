"""
Client Adapters for exporting proxies to various formats.
Supports Surge, Loon, Quantumult X, and SIP008.
"""

import abc
import json
import logging
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
        raise NotImplementedError


class SurgeAdapter(Adapter):
    """Export to Surge 4/5 format."""

    def export(
        self,
        proxies: List[Proxy],
        washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        lines = ["# Surge Policy Export"]

        # 1. Export Standard Proxies
        for p in proxies:
            try:
                line = self._format_proxy(p)
                if line:
                    lines.append(line)
            except Exception as e:
                logger.debug(f"Failed to export {p.protocol} to Surge: {e}")

        # 2. Export Washed Proxies (Converted from Sing-box Outbounds)
        if washed_outbounds:
            for out in washed_outbounds:
                try:
                    # We are looking for the WireGuard Exit nodes that detour to a Relay
                    if (
                        out.get("type") == "wireguard"
                        and out.get("tag", "").startswith("🛡️ Secure")
                        and out.get("detour")
                    ):
                        # Mypy fix: format_singbox_chain_for_surge returns Optional[str], we append only if str
                        chain_line = format_singbox_chain_for_surge(
                            out, washed_outbounds
                        )
                        if chain_line:
                            lines.append(chain_line)
                except Exception as e:
                    logger.debug(f"Failed to export chain to Surge: {e}")

        return "\n".join(lines)

    def _format_proxy(self, p: Proxy) -> str:
        # Format: Name = protocol, address, port, encrypt-method, password, ...
        name = p.remarks if p.remarks else f"{p.protocol}_{p.address}"
        name = name.replace(",", "_").strip()

        if p.protocol in ("ss", "shadowsocks"):
            method = p.details.get("method", "chacha20-ietf-poly1305")
            password = p.details.get("password", "")
            return f"{name} = ss, {p.address}, {p.port}, encrypt-method={method}, password={password}"

        elif p.protocol == "vmess":
            uuid = p.uuid
            return f"{name} = vmess, {p.address}, {p.port}, username={uuid}"

        elif p.protocol == "trojan":
            password = p.uuid  # Trojan uses uuid field as password often in this model
            return f"{name} = trojan, {p.address}, {p.port}, password={password}"

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

        # Use str() to satisfy type checker if fall through, though logic implies we return formatted string or ""
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

        # 2. Export Washed Proxies (Loon WireGuard-over-Proxy)
        if washed_outbounds:
            for out in washed_outbounds:
                try:
                    if (
                        out.get("type") == "wireguard"
                        and out.get("tag", "").startswith("🛡️ Secure")
                        and out.get("detour")
                    ):
                        # Mypy fix: format_singbox_chain_for_loon returns Optional[str]
                        chain_line = format_singbox_chain_for_loon(
                            out, washed_outbounds
                        )
                        if chain_line:
                            lines.append(chain_line)
                except Exception as e:
                    logger.debug(f"Failed to export chain to Loon: {e}")

        return "\n".join(lines)

    def _format_proxy(self, p: Proxy) -> str:
        # Loon is very similar to Surge/Shadowrocket
        name = p.remarks if p.remarks else f"{p.protocol}_{p.address}"
        name = name.replace("=", "_").replace(",", "_").strip()

        if p.protocol == "shadowsocks":
            method = p.details.get("method", "chacha20-ietf-poly1305")
            password = p.details.get("password", "")
            return (
                f'{name} = shadowsocks, {p.address}, {p.port}, {method}, "{password}"'
            )

        elif p.protocol == "vmess":
            uuid = p.uuid
            method = p.details.get("method", "auto")
            return f'{name} = vmess, {p.address}, {p.port}, {method}, "{uuid}"'

        elif p.protocol == "trojan":
            password = p.uuid
            return f'{name} = trojan, {p.address}, {p.port}, "{password}"'

        # Use str() to satisfy type checker if fall through, though logic implies we return formatted string or ""
        return ""


class QuantumultXAdapter(Adapter):
    """Export to Quantumult X format."""

    def export(
        self,
        proxies: List[Proxy],
        washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        lines = []
        for p in proxies:
            try:
                line = self._format_proxy(p)
                if line:
                    lines.append(line)
            except Exception as e:
                logger.debug(f"Failed to export {p.protocol} to QuantumultX: {e}")
        return "\n".join(lines)

    def _format_proxy(self, p: Proxy) -> str:
        # QX Format: protocol=name: host, port, ...
        name = p.remarks if p.remarks else f"{p.protocol}_{p.address}"

        if p.protocol == "shadowsocks":
            method = p.details.get("method", "chacha20-ietf-poly1305")
            password = p.details.get("password", "")
            return f"shadowsocks={name}: {p.address}, {p.port}, method={method}, password={password}"

        elif p.protocol == "vmess":
            uuid = p.uuid
            method = p.details.get("method", "chacha20-poly1305")
            return (
                f"vmess={name}: {p.address}, {p.port}, method={method}, password={uuid}"
            )

        elif p.protocol == "trojan":
            password = p.uuid
            return f"trojan={name}: {p.address}, {p.port}, password={password}"

        # Use str() to satisfy type checker if fall through, though logic implies we return formatted string or ""
        return ""


class SIP008Adapter(Adapter):
    """Export to SIP008 JSON format."""

    def export(
        self,
        proxies: List[Proxy],
        washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        # SIP008 is a JSON format for Shadowsocks delivery
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

        return json.dumps(
            {"version": 1, "servers": servers, "bytes_used": 0, "bytes_remaining": 0},
            indent=2,
        )


def get_adapter(format_name: str) -> Adapter:
    if format_name.lower() == "surge":
        return SurgeAdapter()
    elif format_name.lower() == "loon":
        return LoonAdapter()
    elif format_name.lower() in ["qx", "quantumultx"]:
        return QuantumultXAdapter()
    elif format_name.lower() == "sip008":
        return SIP008Adapter()
    elif format_name.lower() == "shadowrocket":
        return ShadowrocketAdapter()
    else:
        raise ValueError(f"Unknown format: {format_name}")


class ShadowrocketAdapter(Adapter):
    """Export to Shadowrocket format (Base64 encoded links)."""

    def _reconstruct_uri(self, p: Proxy) -> str:
        """Attempt to reconstruct standard URI from proxy object."""
        if p.protocol == "ss" or p.protocol == "shadowsocks":
            # ss://base64(method:password)@server:port#remarks
            import base64

            method = p.details.get("method", "chacha20-ietf-poly1305")
            password = p.details.get("password", "")
            userpass = f"{method}:{password}"
            b64_auth = base64.urlsafe_b64encode(userpass.encode()).decode().rstrip("=")
            return f"ss://{b64_auth}@{p.address}:{p.port}#{p.remarks or 'ConfigStream'}"

        elif p.protocol == "trojan":
            # trojan://password@server:port#remarks
            return (
                f"trojan://{p.uuid}@{p.address}:{p.port}#{p.remarks or 'ConfigStream'}"
            )

        elif p.protocol == "vmess":
            # vmess://base64(json)
            import base64
            import json

            v_obj = {
                "v": "2",
                "ps": p.remarks or "ConfigStream",
                "add": p.address,
                "port": str(p.port),
                "id": p.uuid,
                "aid": str(p.details.get("aid", 0)),
                "scy": p.details.get("scy", "auto"),
                "net": p.details.get("net", "tcp"),
                "type": p.details.get("type", "none"),
                "host": p.details.get("host", ""),
                "path": p.details.get("path", ""),
                "tls": p.details.get("tls", ""),
                "sni": p.details.get("sni", ""),
                "alpn": p.details.get("alpn", ""),
            }
            return "vmess://" + base64.b64encode(json.dumps(v_obj).encode()).decode()

        return ""

    def export(
        self,
        proxies: List[Proxy],
        washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        # Shadowrocket mainly uses standard subscription links (ss://, vmess://, etc.)
        # but can also import Surge/Clash configs.
        # The best "native" format is a list of URI schemes.
        lines = []
        for p in proxies:
            if p.config and "://" in p.config:
                # Use the original config string if available and valid
                lines.append(p.config)
            else:
                # Fallback to reconstruction
                # We try to reconstruct standard URIs for common protocols
                try:
                    uri = self._reconstruct_uri(p)
                    if uri:
                        lines.append(uri)
                except Exception:
                    pass

        # Return as plain text list (decoded subscription)
        return "\n".join(lines)
