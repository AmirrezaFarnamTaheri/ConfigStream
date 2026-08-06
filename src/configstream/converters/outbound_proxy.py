# SPDX-License-Identifier: AGPL-3.0-or-later
"""Convert normalized Sing-box outbound dictionaries back into Proxy models."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..models import Proxy


def proxy_from_outbound(
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
