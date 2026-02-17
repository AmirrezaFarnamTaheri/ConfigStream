# SPDX-License-Identifier: AGPL-3.0-or-later
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
from .utils.bool_parser import parse_tls_flag
from .utils.net import is_ip_literal as _is_ip_literal

logger = logging.getLogger(__name__)


def _extract_sni(details: Dict[str, Any]) -> str:
    for key in (
        "sni",
        "server_name",
        "original_host",
        "host",
        "http_host",
        "ws_host",
    ):
        value = details.get(key)
        if value:
            return str(value)
    return ""


class Adapter(abc.ABC):
    """Base class for proxy adapters."""

    @abc.abstractmethod
    def export(
        self,
        proxies: List[Proxy],
        washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Export a list of proxies to the adapter's format."""


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

        # 2. Export Washed/Revived/Shielded Chains
        chain_count = 0
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
                except Exception as e:
                    logger.debug(f"Failed to export chain to Loon: {e}")

        logger.info(
            f"Loon export summary: {len(lines) - 1 - chain_count} proxies, {chain_count} chains"
        )
        return "\n".join(lines)

    def _format_proxy(self, p: Proxy) -> str:
        name = p.remarks if p.remarks else f"{p.protocol}_{p.address}"
        name = name.replace("=", "_").replace(",", "_").strip()

        if p.protocol in ("shadowsocks", "ss"):
            method = p.details.get("method", "chacha20-ietf-poly1305")
            password = p.details.get("password", "")
            return (
                f'{name} = shadowsocks, {p.address}, {p.port}, {method}, "{password}"'
            )

        elif p.protocol == "vmess":
            uuid = p.uuid
            method = p.details.get("method", "auto")
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

        elif p.protocol == "vless":
            # Loon VLESS format: name = vless, host, port, uuid
            sni = _extract_sni(p.details)
            sni_part = f", sni={sni}" if sni else ""
            return f'{name} = vless, {p.address}, {p.port}, "{p.uuid}"{sni_part}'

        elif p.protocol in ("hysteria2", "hy2"):
            # Loon Hysteria2
            sni = _extract_sni(p.details)
            sni_part = f", sni={sni}" if sni else ""
            return f'{name} = hysteria2, {p.address}, {p.port}, password="{p.uuid}"{sni_part}'

        elif p.protocol == "tuic":
            # Loon TUIC
            sni = _extract_sni(p.details)
            sni_part = f", sni={sni}" if sni else ""
            return (
                f'{name} = tuic, {p.address}, {p.port}, password="{p.uuid}"{sni_part}'
            )

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
            # QX VLESS format: vless=name: host, port, method=none, uuid=...
            # Note: QX supports VLESS but it requires the 'vless' module/keyword
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


class ShadowrocketAdapter(Adapter):
    """Export to Shadowrocket format (Base64 encoded links or plain URI list)."""

    def _update_fragment(self, raw: str, safe_name: str) -> str:
        base = raw.split("#", 1)[0].strip()
        if not safe_name:
            return base
        return f"{base}#{safe_name}"

    def _rewrite_vmess_name(
        self, raw: str, raw_name: str, safe_name: str
    ) -> Optional[str]:
        if not raw_name:
            return raw
        try:
            payload = raw.split("://", 1)[1].strip()
        except IndexError:
            return None

        # Normalize padding for base64 decoding.
        padded = payload + "=" * (-len(payload) % 4)
        for decoder in (base64.b64decode, base64.urlsafe_b64decode):
            try:
                decoded = decoder(padded.encode())
                data = json.loads(decoded)
                if not isinstance(data, dict):
                    continue
                data["ps"] = raw_name
                encoded = base64.b64encode(
                    json.dumps(data, ensure_ascii=False).encode()
                ).decode()
                return f"vmess://{encoded}#{safe_name}"
            except Exception:  # nosec
                continue
        return None

    def _extract_revived_uri(self, p: Proxy) -> Optional[str]:
        """Try to reconstruct a URI from a revived/chain proxy."""
        details = p.details or {}
        tag = "Revived" if not details.get("use_vwarp") else "Revived-VWARP"
        prefer_chain_first = bool(
            details.get("dns_safe") or details.get("dns_hardened")
        )

        def _extract_from_chain() -> Optional[str]:
            chain_obs = details.get("chain_outbounds")
            if isinstance(chain_obs, list):
                from .generators.plaintext import _proxy_from_outbound

                for ob in chain_obs:
                    if not isinstance(ob, dict) or ob.get("type") == "wireguard":
                        continue
                    relay_proxy = _proxy_from_outbound(ob, remark_prefix=f"[{tag}] ")
                    if relay_proxy:
                        uri_value = self._reconstruct_uri(relay_proxy)
                        if uri_value:
                            return uri_value
                for ob in chain_obs:
                    if not isinstance(ob, dict):
                        continue
                    wg_proxy = _proxy_from_outbound(ob, remark_prefix=f"[{tag}] ")
                    if wg_proxy:
                        uri_value = self._reconstruct_uri(wg_proxy)
                        if uri_value:
                            return uri_value
            return None

        if prefer_chain_first:
            chain_uri = _extract_from_chain()
            if chain_uri:
                return chain_uri

        # Strategy 1: full origin_proxy dict
        origin = details.get("origin_proxy")
        if origin and isinstance(origin, dict):
            try:
                origin_p = Proxy(**origin)
                if prefer_chain_first:
                    resolved_ip = str(
                        origin.get("resolved_ip")
                        or (origin.get("details") or {}).get("resolved_ip")
                        or ""
                    ).strip()
                    if resolved_ip and _is_ip_literal(resolved_ip):
                        origin_p.address = resolved_ip
                        origin_p.resolved_ip = resolved_ip
                origin_p.remarks = f"[{tag}] {origin_p.remarks or origin_p.protocol}"
                uri = self._reconstruct_uri(origin_p)
                if uri:
                    return uri
            except Exception:  # nosec
                pass

        # Strategy 2: compact origin_config
        origin_cfg = details.get("origin_config")
        if origin_cfg and isinstance(origin_cfg, dict):
            try:
                origin_p = Proxy(
                    config=str(origin_cfg.get("config", "")),
                    protocol=str(origin_cfg.get("protocol", "")),
                    address=str(origin_cfg.get("address", "")),
                    port=int(origin_cfg.get("port", 0) or 0),
                    uuid=str(origin_cfg.get("uuid", "")),
                    remarks=f"[{tag}] {origin_cfg.get('remarks', '')}",
                    details=origin_cfg.get("details") or {},
                )
                if prefer_chain_first:
                    resolved_ip = str(
                        origin_cfg.get("resolved_ip")
                        or (origin_cfg.get("details") or {}).get("resolved_ip")
                        or ""
                    ).strip()
                    if resolved_ip and _is_ip_literal(resolved_ip):
                        origin_p.address = resolved_ip
                        origin_p.resolved_ip = resolved_ip
                uri = self._reconstruct_uri(origin_p)
                if uri:
                    return uri
                # Try the raw config as URI
                raw = (origin_p.config or "").strip()
                if raw and "://" in raw:
                    return raw
            except Exception:  # nosec
                pass

        # Strategy 3: extract relay from chain_outbounds
        return _extract_from_chain()

    def export(
        self,
        proxies: List[Proxy],
        washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        lines = []
        reconstructed_count = 0
        for p in proxies:
            # Revived proxies: try to extract origin URI from details
            if p.protocol == "revived" or str(p.config).lower().startswith(
                "revived://"
            ):
                uri = self._extract_revived_uri(p)
                if uri:
                    lines.append(uri)
                    reconstructed_count += 1
                continue

            # Chain proxy with JSON config: try to extract outbound URIs
            raw_cfg = (p.config or "").strip()
            if raw_cfg.startswith("{") and (p.details or {}).get("is_chain"):
                try:
                    cfg = json.loads(raw_cfg)
                    outbounds = cfg.get("outbounds", [])
                    if isinstance(outbounds, list):
                        from .generators.plaintext import _proxy_from_outbound

                        for ob in outbounds:
                            if not isinstance(ob, dict):
                                continue
                            ob_proxy = _proxy_from_outbound(
                                ob, remark_prefix="[Chain] "
                            )
                            if ob_proxy:
                                uri = self._reconstruct_uri(ob_proxy)
                                if uri:
                                    lines.append(uri)
                                    reconstructed_count += 1
                                    break
                except (json.JSONDecodeError, TypeError):
                    pass
                continue

            # Normalize existing URIs to enforce consistent tags and protocols.
            if p.config and "://" in p.config:
                raw = p.config.strip()
                scheme = raw.split("://", 1)[0].lower()
                raw_fragment = ""
                if "#" in raw:
                    raw_fragment = raw.split("#", 1)[1]
                raw_name = (
                    p.remarks or urllib.parse.unquote(raw_fragment) or "ConfigStream"
                )
                safe_name = (
                    urllib.parse.quote(raw_name)
                    if p.remarks or not raw_fragment
                    else raw_fragment
                )

                if scheme == "socks":
                    uri = self._reconstruct_uri(p, name_override=raw_name)
                    if uri:
                        lines.append(uri)
                        reconstructed_count += 1
                        continue

                if scheme == "vmess":
                    updated = self._rewrite_vmess_name(raw, raw_name, safe_name)
                    if updated:
                        lines.append(updated)
                        continue

                lines.append(self._update_fragment(raw, safe_name))
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

    def _reconstruct_uri(self, p: Proxy, name_override: Optional[str] = None) -> str:
        """Reconstruct URI with full protocol support."""
        name = urllib.parse.quote(name_override or p.remarks or "ConfigStream")

        def _join_list(value: Any) -> str:
            if isinstance(value, (list, tuple)):
                return ",".join(str(item) for item in value if item)
            return str(value) if value is not None else ""

        if p.protocol in ("ss", "shadowsocks"):
            method = p.details.get("method", "chacha20-ietf-poly1305")
            password = p.details.get("password", "")
            userpass = f"{method}:{password}"
            b64_auth = base64.urlsafe_b64encode(userpass.encode()).decode().rstrip("=")

            # Add plugin support to URIs
            plugin_part = ""
            if "plugin" in p.details:
                plugin = p.details["plugin"]
                opts = p.details.get("plugin_opts", "")
                plugin_str = urllib.parse.quote(f"{plugin};{opts}")
                # Plugin param must be part of the query string, before the fragment
                plugin_part = f"plugin={plugin_str}"

            # Construct query
            query = ""
            if plugin_part:
                query = f"?{plugin_part}"

            return f"ss://{b64_auth}@{p.address}:{p.port}{query}#{name}"

        elif p.protocol == "trojan":
            params = {}
            sni = p.details.get("sni", "")
            if sni:
                params["peer"] = sni
                params["sni"] = sni
            net = p.details.get("net") or p.details.get("type")
            if net:
                params["type"] = net
            path = (
                p.details.get("path")
                or p.details.get("ws_path")
                or p.details.get("http_path")
            )
            if path:
                params["path"] = path
            host = p.details.get("host") or p.details.get("http_host")
            if host:
                params["host"] = host
            service_name = p.details.get("serviceName") or p.details.get(
                "grpc_service_name"
            )
            if service_name:
                params["serviceName"] = service_name
            query = urllib.parse.urlencode(params, safe=",") if params else ""
            query_part = f"?{query}" if query else ""
            return f"trojan://{p.uuid}@{p.address}:{p.port}{query_part}#{name}"

        elif p.protocol == "vmess":
            tls_enabled = parse_tls_flag(p.details.get("tls")) or p.details.get(
                "security"
            ) in ("tls", "reality")
            net = p.details.get("net") or p.details.get("type") or "tcp"
            v_obj = {
                "v": "2",
                "ps": p.remarks or "ConfigStream",
                "add": p.address,
                "port": str(p.port),
                "id": p.uuid,
                "aid": "0",
                "net": net,
                "type": "none",
                "host": p.details.get("host", ""),
                "tls": "tls" if tls_enabled else "",
            }
            path = p.details.get("path") or p.details.get("ws_path")
            if path:
                v_obj["path"] = path
            sni = p.details.get("sni")
            if sni:
                v_obj["sni"] = sni
            alpn = p.details.get("alpn")
            if alpn:
                v_obj["alpn"] = _join_list(alpn)
            fp = p.details.get("fp") or p.details.get("fingerprint")
            if fp:
                v_obj["fp"] = fp
            return "vmess://" + base64.b64encode(json.dumps(v_obj).encode()).decode()

        elif p.protocol == "vless":
            # vless://uuid@host:port?params#name
            params = {}
            security = p.details.get("security")
            if not security:
                security = "tls" if parse_tls_flag(p.details.get("tls")) else "none"
            if security:
                params["security"] = security
            sni = p.details.get("sni", "")
            if sni:
                params["sni"] = sni
            net = p.details.get("net") or p.details.get("type") or "tcp"
            if net:
                params["type"] = net
            flow = p.details.get("flow")
            if flow:
                params["flow"] = flow
            encryption = p.details.get("encryption")
            if encryption:
                params["encryption"] = encryption
            host = p.details.get("host") or p.details.get("http_host")
            if host:
                params["host"] = host
            path = (
                p.details.get("path")
                or p.details.get("ws_path")
                or p.details.get("http_path")
            )
            if path:
                params["path"] = path
            service_name = p.details.get("serviceName") or p.details.get(
                "grpc_service_name"
            )
            if service_name:
                params["serviceName"] = service_name
            pbk = (
                p.details.get("pbk")
                or p.details.get("publicKey")
                or p.details.get("public_key")
            )
            if pbk:
                params["pbk"] = pbk
            sid = (
                p.details.get("sid")
                or p.details.get("shortId")
                or p.details.get("short_id")
            )
            if sid:
                params["sid"] = sid
            fp = p.details.get("fp") or p.details.get("fingerprint")
            if fp:
                params["fp"] = fp
            alpn = p.details.get("alpn")
            if alpn:
                params["alpn"] = _join_list(alpn)
            query = urllib.parse.urlencode(params, safe=",") if params else ""
            query_part = f"?{query}" if query else ""
            return f"vless://{p.uuid}@{p.address}:{p.port}{query_part}#{name}"

        elif p.protocol in ("hysteria2", "hy2"):
            # hysteria2://password@host:port?sni=...#name
            sni = p.details.get("sni", "")
            params = {}
            if sni:
                params["sni"] = sni
            alpn = p.details.get("alpn")
            if alpn:
                params["alpn"] = _join_list(alpn)
            query = urllib.parse.urlencode(params, safe=",") if params else ""
            query_part = f"?{query}" if query else ""
            return f"hysteria2://{p.uuid}@{p.address}:{p.port}{query_part}#{name}"

        elif p.protocol == "tuic":
            # tuic://uuid:password@host:port?sni=...#name
            # TUIC V5 usually just uses UUID as auth or uuid:pass
            sni = p.details.get("sni", "")
            password = p.details.get("password", "")
            query = f"?sni={urllib.parse.quote(sni)}" if sni else ""
            return f"tuic://{p.uuid}:{password}@{p.address}:{p.port}{query}#{name}"

        elif p.protocol in ("http", "socks5", "socks4", "socks"):
            scheme = "socks5" if p.protocol == "socks" else p.protocol
            if scheme == "http":
                scheme = "https" if parse_tls_flag(p.details.get("tls")) else "http"
            user = p.uuid or ""
            password = p.details.get("password", "")
            auth = ""
            if user:
                auth_user = urllib.parse.quote(user)
                if password:
                    auth_pass = urllib.parse.quote(password)
                    auth = f"{auth_user}:{auth_pass}@"
                else:
                    auth = f"{auth_user}@"
            return f"{scheme}://{auth}{p.address}:{p.port}#{name}"

        elif p.protocol == "naive":
            user = p.uuid or ""
            password = p.details.get("password", "")
            if not user or not password:
                return ""
            scheme = (
                "naive+https" if parse_tls_flag(p.details.get("tls")) else "naive+http"
            )
            auth_user = urllib.parse.quote(user)
            auth_pass = urllib.parse.quote(password)
            return f"{scheme}://{auth_user}:{auth_pass}@{p.address}:{p.port}#{name}"

        elif p.protocol == "ssh":
            user = p.uuid or ""
            password = p.details.get("password", "")
            auth = ""
            if user:
                auth_user = urllib.parse.quote(user)
                if password:
                    auth_pass = urllib.parse.quote(password)
                    auth = f"{auth_user}:{auth_pass}@"
                else:
                    auth = f"{auth_user}@"
            return f"ssh://{auth}{p.address}:{p.port}#{name}"

        elif p.protocol == "wireguard":
            priv = p.details.get("private_key", "")
            pub = p.details.get("peer_public_key", "")
            if not priv or not pub:
                return ""
            wg_params: Dict[str, str] = {"publickey": pub}
            local_addr = p.details.get("local_address")
            if isinstance(local_addr, list) and local_addr:
                wg_params["address"] = ",".join(str(a) for a in local_addr)
            elif isinstance(local_addr, str) and local_addr:
                wg_params["address"] = local_addr
            reserved = p.details.get("reserved")
            if isinstance(reserved, list) and reserved:
                wg_params["reserved"] = ",".join(str(r) for r in reserved)
            mtu = p.details.get("mtu")
            if mtu:
                wg_params["mtu"] = str(mtu)
            query = urllib.parse.urlencode(wg_params) if wg_params else ""
            query_part = f"?{query}" if query else ""
            encoded_key = urllib.parse.quote(priv, safe="")
            return f"wireguard://{encoded_key}@{p.address}:{p.port}{query_part}#{name}"

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


_ADAPTER_MAP = {
    "surge": SurgeAdapter,
    "loon": LoonAdapter,
    "qx": QuantumultXAdapter,
    "quantumultx": QuantumultXAdapter,
    "sip008": SIP008Adapter,
    "shadowrocket": ShadowrocketAdapter,
}


def get_adapter(format_name: str) -> Adapter:
    cls = _ADAPTER_MAP.get(format_name.lower())
    if cls is None:
        raise ValueError(f"Unknown format: {format_name}")
    return cls()  # type: ignore[abstract]
