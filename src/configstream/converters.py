"""
Output Converter Helpers.
Moved here to avoid circular imports between output.py and washer.py.
"""

from typing import Any, Dict, Optional, List
from .models import Proxy


def _safe_int_conversion(value: Any, default: int = 0) -> int:
    """
    Safely convert a value to int, handling bytes and other types.
    """
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, bytes):
        try:
            return int(value.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            try:
                return int.from_bytes(value, byteorder="big", signed=False)
            except (ValueError, OverflowError):
                return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def to_clash_proxy(proxy: Proxy) -> Optional[Dict[str, Any]]:
    """Convert internal Proxy model to Clash dictionary."""

    def _add_transport_opts(
        base: Dict[str, Any], details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Helper to add ws/grpc/http options to Clash config."""
        net = details.get("net") or details.get("type") or "tcp"
        base["network"] = net

        if net == "ws":
            ws_opts: Dict[str, Any] = {}
            if "path" in details:
                ws_opts["path"] = str(details["path"])
            if "host" in details or "sni" in details:
                ws_opts["headers"] = {
                    "Host": str(details.get("host") or details.get("sni"))
                }
            if ws_opts:
                base["ws-opts"] = ws_opts

        elif net == "grpc":
            grpc_opts: Dict[str, Any] = {}
            if "serviceName" in details:
                grpc_opts["grpc-service-name"] = str(details["serviceName"])
            if grpc_opts:
                base["grpc-opts"] = grpc_opts

        elif net == "h2" or net == "http":
            h2_opts: Dict[str, Any] = {}
            if "path" in details:
                h2_opts["path"] = [str(details["path"])]
            if "host" in details:
                h2_opts["host"] = [str(details["host"])]
            if h2_opts:
                base["h2-opts"] = h2_opts

        # Common TLS fields
        if details.get("tls") == "tls" or details.get("security") in ["tls", "reality"]:
            base["tls"] = True
            if "sni" in details:
                base["servername"] = str(details["sni"])
            if "fp" in details:
                base["client-fingerprint"] = str(details["fp"])
            if details.get("security") == "reality":
                base["client-fingerprint"] = str(details.get("fp", "chrome"))
                base["reality-opts"] = {
                    "public-key": str(details.get("pbk")),
                    "short-id": str(details.get("sid", "")),
                }

        return base

    base: Dict[str, Any] = {}

    if proxy.protocol == "vmess":
        base = {
            "type": "vmess",
            "server": proxy.address,
            "port": proxy.port,
            "uuid": proxy.uuid,
            "alterId": _safe_int_conversion(proxy.details.get("aid"), 0),
            "cipher": str(proxy.details.get("scy", "auto")),
        }
        return _add_transport_opts(base, proxy.details)

    elif proxy.protocol == "vless":
        base = {
            "type": "vless",
            "server": proxy.address,
            "port": proxy.port,
            "uuid": proxy.uuid,
            "flow": str(proxy.details.get("flow", "")),
        }
        return _add_transport_opts(base, proxy.details)

    elif proxy.protocol == "shadowsocks":
        return {
            "type": "ss",
            "server": proxy.address,
            "port": proxy.port,
            "cipher": str(proxy.details.get("method", "chacha20-ietf-poly1305")),
            "password": str(proxy.details.get("password", "")),
        }
    elif proxy.protocol == "trojan":
        return {
            "type": "trojan",
            "server": proxy.address,
            "port": proxy.port,
            "password": proxy.uuid,
            "udp": True,
        }
    elif proxy.protocol == "http":
        return {
            "type": "http",
            "server": proxy.address,
            "port": proxy.port,
            "username": proxy.uuid if proxy.uuid else None,
            "password": (
                str(proxy.details.get("password", ""))
                if proxy.details.get("password")
                else None
            ),
            "tls": proxy.details.get("tls") == "tls",
        }
    elif proxy.protocol == "socks5":
        return {
            "type": "socks5",
            "server": proxy.address,
            "port": proxy.port,
            "username": proxy.uuid if proxy.uuid else None,
            "password": (
                str(proxy.details.get("password", ""))
                if proxy.details.get("password")
                else None
            ),
            "tls": proxy.details.get("tls") == "tls",
        }
    elif proxy.protocol == "wireguard":
        return {
            "type": "wireguard",
            "server": proxy.address,
            "port": proxy.port,
            "ip": str(proxy.details.get("local_address", "10.10.0.2")),
            "private-key": str(proxy.details.get("private_key")),
            "public-key": str(proxy.details.get("peer_public_key")),
            "udp": True,
        }

    return None


def to_singbox_outbound(proxy: Proxy) -> Optional[Dict[str, Any]]:
    """Convert internal Proxy model to Sing-box outbound."""
    base: Dict[str, Any] = {
        "server": proxy.address,
        "server_port": proxy.port,
    }

    def _add_transport_sb(
        out: Dict[str, Any], details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Helper to add transport options for Sing-box."""
        net = details.get("net") or details.get("type") or "tcp"

        transport: Dict[str, Any] = {}
        if net == "ws":
            transport["type"] = "ws"
            if "path" in details:
                transport["path"] = str(details["path"])
            if "host" in details or "sni" in details:
                transport["headers"] = {
                    "Host": str(details.get("host") or details.get("sni"))
                }
        elif net == "grpc":
            transport["type"] = "grpc"
            if "serviceName" in details:
                transport["service_name"] = str(details["serviceName"])
        elif net == "http" or net == "h2":
            transport["type"] = "http"
            if "path" in details:
                transport["path"] = str(details["path"])
            if "host" in details:
                transport["host"] = [str(details["host"])]

        if transport:
            out["transport"] = transport

        # TLS
        if details.get("tls") == "tls" or details.get("security") in ["tls", "reality"]:
            tls: Dict[str, Any] = {"enabled": True}
            if "sni" in details:
                tls["server_name"] = str(details["sni"])
            if "fp" in details:
                tls["utls"] = {"enabled": True, "fingerprint": str(details["fp"])}

            if details.get("security") == "reality":
                tls["reality"] = {
                    "enabled": True,
                    "public_key": str(details.get("pbk")),
                    "short_id": str(details.get("sid", "")),
                }

            out["tls"] = tls

        return out

    if proxy.protocol == "vmess":
        out = {
            "type": "vmess",
            **base,
            "uuid": proxy.uuid,
            "security": "auto",
            "alter_id": _safe_int_conversion(proxy.details.get("aid"), 0),
        }
        return _add_transport_sb(out, proxy.details)

    elif proxy.protocol == "vless":
        out = {
            "type": "vless",
            **base,
            "uuid": proxy.uuid,
            "flow": str(proxy.details.get("flow", "")),
        }
        return _add_transport_sb(out, proxy.details)

    elif proxy.protocol == "shadowsocks":
        return {
            "type": "shadowsocks",
            **base,
            "method": str(proxy.details.get("method", "chacha20-ietf-poly1305")),
            "password": str(proxy.details.get("password", "")),
        }
    elif proxy.protocol == "trojan":
        return {"type": "trojan", **base, "password": proxy.uuid}

    elif proxy.protocol == "http":
        return {
            "type": "http",
            **base,
            "username": proxy.uuid if proxy.uuid else "",
            "password": str(proxy.details.get("password", "")),
            "tls": {"enabled": proxy.details.get("tls") == "tls"},
        }
    elif proxy.protocol == "socks5":
        return {
            "type": "socks",
            **base,
            "username": proxy.uuid if proxy.uuid else "",
            "password": str(proxy.details.get("password", "")),
        }
    elif proxy.protocol == "wireguard":
        return {
            "type": "wireguard",
            **base,
            "local_address": [str(proxy.details.get("local_address", "10.10.0.2/32"))],
            "private_key": str(proxy.details.get("private_key")),
            "peer_public_key": str(proxy.details.get("peer_public_key", "")),
        }
    elif proxy.protocol == "hysteria2":
        out = {
            "type": "hysteria2",
            **base,
            "password": proxy.uuid or str(proxy.details.get("password", "")),
        }
        out["tls"] = {
            "enabled": True,
            "server_name": str(proxy.details.get("sni", "")),
            "insecure": bool(proxy.details.get("allowInsecure", False)),
            "alpn": proxy.details.get("alpn", []),
        }
        if proxy.details.get("obfs-type") == "salamander":
            out["obfs"] = {
                "type": "salamander",
                "password": str(proxy.details.get("obfs-password", "")),
            }
        return out

    elif proxy.protocol == "tuic":
        out = {
            "type": "tuic",
            **base,
            "uuid": proxy.uuid,
            "password": str(proxy.details.get("password", "")),
            "congestion_controller": str(
                proxy.details.get("congestion_controller", "bbr")
            ),
        }
        out["tls"] = {
            "enabled": True,
            "server_name": str(proxy.details.get("sni", "")),
            "alpn": proxy.details.get("alpn", []),
        }
        return out

    return None
