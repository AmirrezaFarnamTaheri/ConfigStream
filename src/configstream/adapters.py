"""
Protocol Adapters for Client Configurations.
Converts normalized Proxy objects into client-specific schemas (Clash, Sing-box).
"""

from __future__ import annotations
from typing import Any, Dict, Optional
from .models import Proxy

def _clean_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively remove None/Empty values."""
    clean = {}
    for k, v in d.items():
        if isinstance(v, dict):
            nested = _clean_dict(v)
            if nested:
                clean[k] = nested
        elif v is not None and v != "":
            clean[k] = v
    return clean

# --- CLASH META (MIHOMO) ADAPTERS ---

def to_clash_proxy(proxy: Proxy) -> Optional[Dict[str, Any]]:
    """Convert Proxy to Clash Meta (Mihomo) dictionary format."""
    base = {
        "name": proxy.remarks or f"{proxy.protocol}:{proxy.port}",
        "server": proxy.address,
        "port": int(proxy.port),
        "type": proxy.protocol,
    }

    details = proxy.details or {}

    # Common Transport Options
    network = details.get("net") or details.get("network", "tcp")
    base["network"] = network

    # TLS / SNI
    if details.get("tls") in ["tls", "xtls", "1", "true"] or proxy.sni:
        base["tls"] = True
        base["servername"] = proxy.sni or details.get("host") or proxy.address
        base["skip-cert-verify"] = details.get("allowInsecure") == "1"
        if details.get("alpn"):
            base["alpn"] = details.get("alpn")

    # Fingerprint (uTLS)
    if details.get("fp"):
        base["client-fingerprint"] = details.get("fp")

    # Transport Specifics
    if network == "ws":
        base["ws-opts"] = {
            "path": proxy.path,
            "headers": {"Host": details.get("host") or base.get("servername")}
        }
    elif network == "grpc":
        base["grpc-opts"] = {
            "grpc-service-name": details.get("serviceName") or proxy.path
        }

    # Protocol Specifics
    if proxy.protocol == "vmess":
        base["uuid"] = proxy.uuid
        base["alterId"] = int(details.get("aid", 0))
        base["cipher"] = details.get("scy", "auto")
        # UDP is usually supported
        base["udp"] = True

    elif proxy.protocol == "vless":
        base["uuid"] = proxy.uuid
        base["flow"] = details.get("flow", "")
        base["udp"] = True
        # Reality Support (Clash Meta)
        if details.get("security") == "reality":
            base["client-fingerprint"] = details.get("fp", "chrome")
            base["reality-opts"] = {
                "public-key": details.get("pbk"),
                "short-id": details.get("sid")
            }

    elif proxy.protocol == "trojan":
        base["password"] = proxy.uuid
        base["udp"] = True

    elif proxy.protocol == "shadowsocks":
        base["cipher"] = details.get("method", "chacha20-ietf-poly1305")
        base["password"] = proxy.uuid
        base["udp"] = True

    elif proxy.protocol == "hysteria2":
        base["password"] = proxy.uuid
        base["sni"] = base.get("servername")  # Hy2 uses sni key
        base["obfs"] = details.get("obfs", "")
        base["obfs-password"] = details.get("obfs-password", "")
        base["up"] = details.get("up_mbps", "")
        base["down"] = details.get("down_mbps", "")

    elif proxy.protocol == "tuic":
        base["uuid"] = proxy.uuid
        base["password"] = proxy.uuid
        base["congestion-controller"] = details.get("congestion_controller", "bbr")

    else:
        # Unsupported in Clash
        return None

    return _clean_dict(base)

# --- SING-BOX ADAPTERS ---

def to_singbox_outbound(proxy: Proxy) -> Optional[Dict[str, Any]]:
    """Convert Proxy to Sing-box outbound object."""
    out = {
        "type": proxy.protocol,
        "tag": proxy.remarks or f"{proxy.protocol}-{proxy.address}",
        "server": proxy.address,
        "server_port": int(proxy.port),
    }

    details = proxy.details or {}

    # Credentials
    if proxy.protocol in ["vmess", "vless"]:
        out["uuid"] = proxy.uuid
    elif proxy.protocol in ["trojan", "hysteria2", "tuic"]:
        out["password"] = proxy.uuid
    elif proxy.protocol == "shadowsocks":
        out["method"] = details.get("method", "chacha20-ietf-poly1305")
        out["password"] = proxy.uuid

    # Protocol Specifics
    if proxy.protocol == "vmess":
        out["alter_id"] = int(details.get("aid", 0))
        out["security"] = details.get("scy", "auto")
    elif proxy.protocol == "vless":
        out["flow"] = details.get("flow", "")
    elif proxy.protocol == "hysteria2":
        if details.get("obfs"):
            out["obfs"] = {
                "type": "salamander",
                "password": details.get("obfs-password")
            }

    # TLS Configuration
    tls_type = details.get("security", "")
    if tls_type in ["tls", "reality"] or proxy.protocol in ["hysteria2", "tuic"]:
        tls_conf = {
            "enabled": True,
            "server_name": proxy.sni or details.get("host") or proxy.address,
            "insecure": details.get("allowInsecure") == "1",
            "utls": {"enabled": True, "fingerprint": details.get("fp", "chrome")}
        }
        if details.get("alpn"):
            tls_conf["alpn"] = details.get("alpn")

        if tls_type == "reality":
            tls_conf["reality"] = {
                "enabled": True,
                "public_key": details.get("pbk"),
                "short_id": details.get("sid")
            }

        out["tls"] = tls_conf

    # Transport Configuration
    net = details.get("net") or details.get("network")
    if net in ["ws", "grpc", "httpupgrade"]:
        transport = {"type": net}
        if net == "ws":
            transport["path"] = proxy.path
            if details.get("host"):
                transport["headers"] = {"Host": details.get("host")}
        elif net == "grpc":
            transport["service_name"] = details.get("serviceName") or proxy.path

        out["transport"] = transport

    # Multiplexing (Default to enabled for VMess/VLESS/Trojan)
    if proxy.protocol in ["vmess", "vless", "trojan"]:
        out["multiplex"] = {"enabled": True, "padding": True}

    return _clean_dict(out)
