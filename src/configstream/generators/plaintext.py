# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import logging
import re
import urllib.parse
from typing import Any, Dict, List, Optional

from ..adapters import ShadowrocketAdapter
from ..filtering import proxy_unique_key
from ..models import Proxy
from ..utils.net import is_ip_literal as _is_ip_literal

logger = logging.getLogger(__name__)

_URI_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")


def _normalize_uri_key(uri: str) -> str:
    return uri.split("#", 1)[0].strip()


def _dedupe_key(proxy: Proxy, uri: str) -> object:
    scheme = uri.split("://", 1)[0].lower()
    if scheme == "vmess":
        return ("vmess", proxy_unique_key(proxy))
    return _normalize_uri_key(uri)


def _proxy_from_outbound(
    ob: Dict[str, Any], remark_prefix: str = ""
) -> Optional[Proxy]:
    """Attempt to build a minimal Proxy from a sing-box outbound dict."""
    ob_type = ob.get("type", "")
    server = ob.get("server", "")
    port = ob.get("server_port", 0)
    if not server or not port:
        return None
    try:
        port = int(port)
    except (TypeError, ValueError):
        return None
    if port <= 0 or port > 65535:
        return None

    # Map sing-box types to our protocol names
    proto_map = {
        "shadowsocks": "shadowsocks",
        "vmess": "vmess",
        "vless": "vless",
        "trojan": "trojan",
        "hysteria2": "hysteria2",
        "hysteria": "hysteria",
        "tuic": "tuic",
        "wireguard": "wireguard",
        "http": "http",
        "socks": "socks5",
    }
    protocol = proto_map.get(ob_type)
    if not protocol:
        return None

    details: Dict[str, Any] = {}
    uuid_val = ""

    if protocol == "shadowsocks":
        details["method"] = ob.get("method", "")
        details["password"] = ob.get("password", "")
    elif protocol in ("vmess", "vless"):
        uuid_val = ob.get("uuid", "")
        tls_obj = ob.get("tls") if isinstance(ob.get("tls"), dict) else {}
        if tls_obj:
            details["sni"] = tls_obj.get("server_name", "")
            if tls_obj.get("enabled"):
                details["tls"] = "tls"
                reality = tls_obj.get("reality")
                if isinstance(reality, dict) and reality.get("enabled"):
                    details["security"] = "reality"
                    details["pbk"] = reality.get("public_key", "")
                    details["sid"] = reality.get("short_id", "")
            alpn = tls_obj.get("alpn")
            if alpn:
                details["alpn"] = alpn
            utls = tls_obj.get("utls")
            if isinstance(utls, dict) and utls.get("fingerprint"):
                details["fp"] = utls["fingerprint"]
        transport = ob.get("transport") if isinstance(ob.get("transport"), dict) else {}
        if transport:
            details["type"] = transport.get("type", "")
            if transport.get("path"):
                details["path"] = transport["path"]
            if transport.get("host"):
                details["host"] = transport["host"]
            if transport.get("service_name"):
                details["serviceName"] = transport["service_name"]
        if protocol == "vless":
            flow = ob.get("flow", "")
            if flow:
                details["flow"] = flow
    elif protocol == "trojan":
        uuid_val = ob.get("password", "")
        tls_obj = ob.get("tls") if isinstance(ob.get("tls"), dict) else {}
        if tls_obj:
            details["sni"] = tls_obj.get("server_name", "")
        transport = ob.get("transport") if isinstance(ob.get("transport"), dict) else {}
        if transport:
            details["type"] = transport.get("type", "")
            if transport.get("path"):
                details["path"] = transport["path"]
            if transport.get("host"):
                details["host"] = transport["host"]
    elif protocol == "hysteria2":
        uuid_val = ob.get("password", "")
    elif protocol == "wireguard":
        details["private_key"] = ob.get("private_key", "")
        details["peer_public_key"] = ob.get("peer_public_key", "")
        details["local_address"] = ob.get("local_address", [])
        details["reserved"] = ob.get("reserved", [])
        details["mtu"] = ob.get("mtu")

    tag = ob.get("tag", protocol)
    remarks = f"{remark_prefix}{tag}" if remark_prefix else tag

    return Proxy(
        config="",
        protocol=protocol,
        address=str(server),
        port=port,
        uuid=str(uuid_val),
        remarks=remarks,
        details=details,
    )


def _extract_uri(proxy: Proxy, adapter: ShadowrocketAdapter) -> Optional[str]:
    # Revived proxies: reconstruct URI from origin data stored in details
    if proxy.protocol == "revived" or (proxy.config or "").lower().startswith(
        "revived://"
    ):
        details = proxy.details or {}
        tag = "Revived" if not details.get("use_vwarp") else "Revived-VWARP"
        prefer_chain_first = bool(
            details.get("dns_safe") or details.get("dns_hardened")
        )

        def _extract_from_chain() -> Optional[str]:
            chain_obs = details.get("chain_outbounds")
            if not isinstance(chain_obs, list):
                return None
            for ob in chain_obs:
                if not isinstance(ob, dict):
                    continue
                # Skip wireguard hops (WARP endpoints) — prefer the relay
                if ob.get("type") == "wireguard":
                    continue
                relay_proxy = _proxy_from_outbound(ob, remark_prefix=f"[{tag}] ")
                if relay_proxy:
                    uri_value = _extract_uri(relay_proxy, adapter)
                    if uri_value:
                        return uri_value
            # If only wireguard hops remain, try the first one
            for ob in chain_obs:
                if not isinstance(ob, dict):
                    continue
                wg_proxy = _proxy_from_outbound(ob, remark_prefix=f"[{tag}] ")
                if wg_proxy:
                    uri_value = _extract_uri(wg_proxy, adapter)
                    if uri_value:
                        return uri_value
            return None

        if prefer_chain_first:
            chain_uri = _extract_from_chain()
            if chain_uri:
                return chain_uri

        # Strategy 1: full origin_proxy dict (available in-memory before serialization)
        origin = details.get("origin_proxy")
        if origin and isinstance(origin, dict):
            try:
                origin_proxy = Proxy(**origin)
                applied_ip_override = False
                if prefer_chain_first:
                    resolved_ip = str(
                        origin.get("resolved_ip")
                        or (origin.get("details") or {}).get("resolved_ip")
                        or ""
                    ).strip()
                    if resolved_ip and _is_ip_literal(resolved_ip):
                        origin_proxy.address = resolved_ip
                        origin_proxy.resolved_ip = resolved_ip
                        applied_ip_override = True
                origin_proxy.remarks = (
                    f"[{tag}] {origin_proxy.remarks or origin_proxy.protocol}"
                )
                if applied_ip_override:
                    # Force field-based URI reconstruction with overridden address.
                    origin_proxy.config = ""
                return _extract_uri(origin_proxy, adapter)
            except Exception:
                pass

        # Strategy 2: compact origin_config (preserved after serialization)
        origin_cfg = details.get("origin_config")
        if origin_cfg and isinstance(origin_cfg, dict):
            try:
                origin_proxy = Proxy(
                    config=str(origin_cfg.get("config", "")),
                    protocol=str(origin_cfg.get("protocol", "")),
                    address=str(origin_cfg.get("address", "")),
                    port=int(origin_cfg.get("port", 0) or 0),
                    uuid=str(origin_cfg.get("uuid", "")),
                    remarks=f"[{tag}] {origin_cfg.get('remarks', '')}",
                    details=origin_cfg.get("details") or {},
                )
                applied_ip_override = False
                if prefer_chain_first:
                    resolved_ip = str(
                        origin_cfg.get("resolved_ip")
                        or (origin_cfg.get("details") or {}).get("resolved_ip")
                        or ""
                    ).strip()
                    if resolved_ip and _is_ip_literal(resolved_ip):
                        origin_proxy.address = resolved_ip
                        origin_proxy.resolved_ip = resolved_ip
                        applied_ip_override = True
                if applied_ip_override:
                    # Force field-based URI reconstruction with overridden address.
                    origin_proxy.config = ""
                return _extract_uri(origin_proxy, adapter)
            except Exception:
                pass

        # Strategy 3: extract relay outbound from chain_outbounds
        chain_uri = _extract_from_chain()
        if chain_uri:
            return chain_uri

        return None

    # Chain proxy with JSON config: try to extract outbounds
    raw = (proxy.config or "").strip()
    if raw.startswith("{") and (proxy.details or {}).get("is_chain"):
        try:
            cfg = json.loads(raw)
            outbounds = cfg.get("outbounds", [])
            if isinstance(outbounds, list):
                for ob in outbounds:
                    if not isinstance(ob, dict):
                        continue
                    ob_proxy = _proxy_from_outbound(ob, remark_prefix="[Chain] ")
                    if ob_proxy:
                        uri = adapter._reconstruct_uri(ob_proxy)
                        if uri:
                            return uri
        except (json.JSONDecodeError, TypeError):
            pass
        return None

    if raw and _URI_PATTERN.match(raw):
        scheme = raw.split("://", 1)[0].lower()
        if scheme == "vmess" or scheme == "socks":
            rebuilt = adapter._reconstruct_uri(proxy)
            if rebuilt:
                return rebuilt
        if proxy.remarks:
            safe_name = urllib.parse.quote(proxy.remarks)
            base = raw.split("#", 1)[0]
            return f"{base}#{safe_name}"
        return raw

    return adapter._reconstruct_uri(proxy) or None


def _sanitize_uri(uri: str) -> Optional[str]:
    """Reject URIs containing null bytes or non-printable binary data."""
    if "\x00" in uri:
        return None
    # URL-encode any remaining raw bytes that slipped through parsers
    # (e.g. TLS prefix obfuscation fields with raw binary)
    try:
        uri.encode("utf-8")
    except UnicodeEncodeError:
        return None
    return uri


def generate_plaintext_subscription(proxies: List[Proxy]) -> str:
    adapter = ShadowrocketAdapter()
    seen: set[object] = set()
    lines: List[str] = []
    protocol_order = [
        "shadowsocks",
        "ss2022",
        "vless",
        "vmess",
        "trojan",
        "hysteria2",
        "hysteria",
        "tuic",
        "wireguard",
        "naive",
        "ssh",
        "http",
        "socks5",
        "socks4",
        "socks",
        "revived",
    ]

    grouped: dict[str, List[Proxy]] = {}
    for proxy in proxies:
        proto_key = proxy.protocol or "unknown"
        if proto_key == "socks":
            proto_key = "socks5"
        elif proto_key == "ss":
            proto_key = "shadowsocks"
        elif proto_key == "hy2":
            proto_key = "hysteria2"
        elif proto_key == "wg":
            proto_key = "wireguard"
        grouped.setdefault(proto_key, []).append(proxy)

    ordered_protocols = protocol_order + sorted(
        [p for p in grouped.keys() if p not in protocol_order]
    )

    for proto in ordered_protocols:
        for proxy in grouped.get(proto, []):
            uri = _extract_uri(proxy, adapter)
            if not uri:
                continue
            uri = _sanitize_uri(uri)
            if not uri:
                continue
            dedupe_key = _dedupe_key(proxy, uri)
            if not dedupe_key or dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            lines.append(uri)

    return "\n".join(lines)
