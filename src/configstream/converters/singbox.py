import logging
import hashlib
from typing import Any, Dict, Optional
from ..models import Proxy
from ..security_validator import SecurityValidator
from .singbox_utils import add_transport_sb, apply_stealth_profile

logger = logging.getLogger(__name__)


def to_singbox_outbound(proxy: Proxy) -> Optional[Dict[str, Any]]:
    """
    Convert a Proxy model to a Sing-box outbound configuration.
    Returns None if conversion fails or proxy is invalid.
    """
    # Early validation - reject invalid proxies before expensive conversion
    if not proxy or not proxy.address or not proxy.port:
        logger.debug(f"Conversion failed: invalid address/port for {proxy}")
        return None

    # Filter subscription URLs that got past parser
    addr_lower = proxy.address.lower()
    if any(
        domain in addr_lower
        for domain in [
            "github.com",
            "githubusercontent.com",
            "gitlab.com",
            "bitbucket.org",
            "t.me",
        ]
    ):
        logger.debug(f"Conversion skipped for subscription URL: {proxy.address}")
        return None

    # Reject invalid port ranges
    if not isinstance(proxy.port, int) or proxy.port <= 0 or proxy.port > 65535:
        logger.warning(
            f"Conversion failed: invalid port {proxy.port} for {proxy.address}"
        )
        return None

    base: Dict[str, Any] = {
        "server": proxy.address,
        "server_port": proxy.port,
    }

    out: Optional[Dict[str, Any]] = None

    if proxy.protocol == "vmess":
        # Validate required UUID
        uuid = proxy.uuid or proxy.details.get("uuid") or proxy.details.get("id")
        if not uuid:
            # [FIX] Elevated to WARNING to surface data quality issues
            logger.warning(
                f"Dropping VMess proxy missing UUID: {proxy.address}:{proxy.port}. "
                f"Source: {proxy.details.get('_source', 'unknown')}"
            )
            return None
        out = {
            "type": "vmess",
            **base,
            "uuid": str(uuid),
            "security": "auto",
            "alter_id": 0,  # [FIX] Enforce 0
        }
        add_transport_sb(out, proxy.details)

    elif proxy.protocol == "vless":
        # Validate required UUID
        uuid = proxy.uuid or proxy.details.get("uuid")
        if not uuid:
            logger.warning(
                f"Dropping VLESS proxy missing UUID: {proxy.address}:{proxy.port}. "
                f"Source: {proxy.details.get('_source', 'unknown')}"
            )
            return None
        out = {
            "type": "vless",
            **base,
            "uuid": str(uuid),
            "flow": str(proxy.details.get("flow", "")),
        }
        add_transport_sb(out, proxy.details)

    elif proxy.protocol == "shadowsocks":
        # Validate required password
        if not proxy.details.get("password"):
            # [FIX] Elevated to WARNING
            logger.warning(
                f"Dropping Shadowsocks proxy missing password: {proxy.address}:{proxy.port}. "
                f"Source: {proxy.details.get('_source', 'unknown')}"
            )
            return None
        out = {
            "type": "shadowsocks",
            **base,
            "method": str(proxy.details.get("method", "chacha20-ietf-poly1305")),
            "password": str(proxy.details.get("password", "")),
        }
        # CRITICAL FIX: Map plugins (obfs-local, v2ray-plugin, etc.)
        if "plugin" in proxy.details:
            out["plugin"] = str(proxy.details["plugin"])
            if "plugin_opts" in proxy.details:
                out["plugin_opts"] = str(proxy.details["plugin_opts"])
            logger.debug(
                f"Mapped Shadowsocks plugin for {proxy.address}: {out['plugin']}"
            )

    elif proxy.protocol == "trojan":
        # Validate required password (stored as uuid)
        password = proxy.uuid or proxy.details.get("password")
        if not password:
            logger.warning(
                f"Dropping Trojan proxy missing password: {proxy.address}:{proxy.port}. "
                f"Source: {proxy.details.get('_source', 'unknown')}"
            )
            return None
        out = {"type": "trojan", **base, "password": str(password)}
        # [FIX] Trojan requires TLS. Force it if not present.
        proxy.details["tls"] = "tls"
        add_transport_sb(out, proxy.details)

    elif proxy.protocol == "http":
        out = {
            "type": "http",
            **base,
            "username": proxy.uuid if proxy.uuid else "",
            "password": str(proxy.details.get("password", "")),
            "tls": {"enabled": proxy.details.get("tls") == "tls"},
        }

    # [FIX] Missing Protocols Implementation
    elif proxy.protocol == "ssh":
        out = {
            "type": "ssh",
            **base,
            "user": proxy.uuid or "root",
            "password": str(proxy.details.get("password", "")),
        }
        if "private_key" in proxy.details:
            out["private_key"] = str(proxy.details["private_key"])
        if "host_key" in proxy.details:
            out["host_key"] = str(proxy.details["host_key"])

    elif proxy.protocol == "hysteria":
        # Map Hysteria v1
        out = {
            "type": "hysteria",
            **base,
            "auth_str": str(proxy.details.get("auth_str", "")),
            "up_mbps": 100,
            "down_mbps": 100,
        }
        out["tls"] = {
            "enabled": True,
            "server_name": str(proxy.details.get("sni", "")),
            "insecure": True,
        }
    elif proxy.protocol == "socks5":
        # Sing-box expects type "socks" for SOCKS5 outbounds.
        out = {
            "type": "socks",
            **base,
            "username": proxy.uuid if proxy.uuid else "",
            "password": str(proxy.details.get("password", "")),
        }
    elif proxy.protocol == "wireguard":
        # [FIX] Generate unique local IP to allow concurrent testing
        # Using 2 bytes from hash to generate a /32 IP in 172.16.0.0/16 range
        # to minimize collision probability during concurrent testing.
        h = hashlib.sha256(f"{proxy.address}:{proxy.port}".encode()).digest()
        octet3 = h[0]
        octet4 = h[1]
        # Ensure fourth octet is not .0 or .1 which can be special
        if octet4 < 2:
            octet4 = 2
        unique_ip = f"172.16.{octet3}.{octet4}/32"

        safe_addr = SecurityValidator.sanitize_address(
            getattr(proxy, "address", "unknown")
        )

        logger.debug(
            f"Generated unique local IP {unique_ip} for WireGuard proxy {safe_addr}"
        )

        private_key = proxy.details.get("private_key") or proxy.uuid
        if not private_key:
            logger.warning(
                f"Dropping WireGuard proxy missing private_key: {proxy.address}:{proxy.port}. "
                f"Source: {proxy.details.get('_source', 'unknown')}"
            )
            return None

        out = {
            "type": "wireguard",
            **base,
            "local_address": [unique_ip],
            "private_key": str(private_key),
            "peer_public_key": str(proxy.details.get("peer_public_key", "")),
        }
        return out

    elif proxy.protocol == "hysteria2":
        out = {
            "type": "hysteria2",
            **base,
            "password": proxy.uuid or str(proxy.details.get("password", "")),
        }
        # [FIX] Default insecure to True for Hysteria2 to improve test yield
        is_insecure = False
        if "allowInsecure" in proxy.details:
            is_insecure = bool(proxy.details["allowInsecure"])

        out["tls"] = {
            "enabled": True,
            "server_name": str(proxy.details.get("sni", "")),
            "insecure": is_insecure,
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
            # [FIX] Changed 'congestion_controller' to 'congestion_control' for sing-box standard
            "congestion_control": str(
                proxy.details.get("congestion_controller", "bbr")
            ),
        }
        # [FIX] Default insecure to True for TUIC
        is_insecure = False
        if "allowInsecure" in proxy.details:
            is_insecure = bool(proxy.details["allowInsecure"])

        out["tls"] = {
            "enabled": True,
            "server_name": str(proxy.details.get("sni", "")),
            "insecure": is_insecure,
            "alpn": proxy.details.get("alpn", []),
        }
        return out

    if out and proxy.protocol in ["vmess", "vless", "trojan", "shadowsocks"]:
        out = apply_stealth_profile(out, proxy.protocol)

    if out:
        safe_addr = SecurityValidator.sanitize_address(
            getattr(proxy, "address", "unknown")
        )
        safe_source = SecurityValidator.sanitize_log_message(
            str(proxy.details.get("_source", "unknown"))
        )
        logger.debug(
            f"Successfully converted {proxy.protocol} proxy: {safe_addr} "
            f"(Source: {safe_source})"
        )
    else:
        details_to_log = proxy.details.copy()
        if "private_key" in details_to_log:
            details_to_log["private_key"] = "[MASKED]"

        # Known unsupported protocols in Sing-box (native)
        if proxy.protocol in ["ssr", "snell", "brook", "juicity", "xray"]:
            logger.debug(
                f"Protocol {proxy.protocol} not supported in Sing-box conversion (skipped). "
                f"Proxy: {proxy.address}"
            )
        else:
            logger.warning(
                f"Dropped {proxy.protocol} proxy {proxy.address} during conversion. "
                f"Reason: Logic fell through (Missing implementation or valid fields). "
                f"Details: {details_to_log}"
            )

    return out
