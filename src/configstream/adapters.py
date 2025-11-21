"""
Client Adapters for exporting proxies to various formats.
Supports Surge, Loon, Quantumult X, and SIP008.
"""

import abc
import json
import logging
from typing import List
from .models import Proxy

logger = logging.getLogger(__name__)


class Adapter(abc.ABC):
    """Base class for proxy adapters."""

    @abc.abstractmethod
    def export(self, proxies: List[Proxy]) -> str:
        """Export a list of proxies to the adapter's format."""
        raise NotImplementedError


class SurgeAdapter(Adapter):
    """Export to Surge 4/5 format."""

    def export(self, proxies: List[Proxy]) -> str:
        lines = ["# Surge Policy Export"]
        for p in proxies:
            try:
                line = self._format_proxy(p)
                if line:
                    lines.append(line)
            except Exception as e:
                logger.debug(f"Failed to export {p.protocol} to Surge: {e}")
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

        return ""


class LoonAdapter(Adapter):
    """Export to Loon format."""

    def export(self, proxies: List[Proxy]) -> str:
        lines = ["# Loon Proxy Export"]
        for p in proxies:
            try:
                line = self._format_proxy(p)
                if line:
                    lines.append(line)
            except Exception as e:
                logger.debug(f"Failed to export {p.protocol} to Loon: {e}")
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

        return ""


class QuantumultXAdapter(Adapter):
    """Export to Quantumult X format."""

    def export(self, proxies: List[Proxy]) -> str:
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

        return ""


class SIP008Adapter(Adapter):
    """Export to SIP008 JSON format."""

    def export(self, proxies: List[Proxy]) -> str:
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
    else:
        raise ValueError(f"Unknown format: {format_name}")
