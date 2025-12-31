import logging
import hashlib
from typing import Any, Dict, Optional
from ..models import Proxy
from ..security_validator import SecurityValidator
from .singbox_utils import add_transport_sb, apply_stealth_profile
from ..utils.bool_parser import parse_bool

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

    # [FIX] Use formatted remarks as tag when available (set by ProxyTagger)
    # Fall back to generated tag if remarks is empty/generic
    if proxy.remarks and proxy.remarks.lower() not in ["", "defaultproxyname", "none"]:
        tag = proxy.remarks
    else:
        tag = f"{proxy.protocol}-{proxy.country_code}-{proxy.id[:8]}"

    base: Dict[str, Any] = {
        "tag": tag,
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
            # [FIX] Don't use str() which converts None to "None" string
            "flow": proxy.details.get("flow") or "",
        }
        add_transport_sb(out, proxy.details)

    elif proxy.protocol in ["shadowsocks", "ss2022"]:
        # [FIX] Handle both Shadowsocks and Shadowsocks 2022
        # SS2022 uses same sing-box type but with 2022-specific cipher methods
        # Validate required password
        if not proxy.details.get("password"):
            # [FIX] Elevated to WARNING
            logger.warning(
                f"Dropping Shadowsocks proxy missing password: {proxy.address}:{proxy.port}. "
                f"Source: {proxy.details.get('_source', 'unknown')}"
            )
            return None

        # SS2022 default method differs from classic SS
        if proxy.protocol == "ss2022":
            default_method = "2022-blake3-aes-128-gcm"
        else:
            default_method = "chacha20-ietf-poly1305"

        # [FIX] Normalize method name (sing-box expects lowercase, no spaces)
        method = str(proxy.details.get("method", default_method)).lower().strip()

        out = {
            "type": "shadowsocks",
            **base,
            "method": method,
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
        # Create a copy to avoid mutating the input proxy object
        details_with_tls = {**proxy.details, "tls": "tls"}
        add_transport_sb(out, details_with_tls)

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
        # [FIX] Parse up/down speeds from config instead of hardcoding
        up_mbps = proxy.details.get("up_mbps") or proxy.details.get("up", 100)
        down_mbps = proxy.details.get("down_mbps") or proxy.details.get("down", 100)
        out = {
            "type": "hysteria",
            **base,
            "auth_str": str(proxy.details.get("auth_str", "")),
            "up_mbps": int(up_mbps) if str(up_mbps).isdigit() else 100,
            "down_mbps": int(down_mbps) if str(down_mbps).isdigit() else 100,
        }
        # [FIX] Respect allowInsecure flag instead of hardcoding True
        is_insecure = False
        if proxy.details.get("allowInsecure") or proxy.details.get("skip_cert_verify"):
            is_insecure = True
        out["tls"] = {
            "enabled": True,
            "server_name": str(proxy.details.get("sni", "")),
            "insecure": is_insecure,
        }
    elif proxy.protocol == "socks5":
        # Sing-box expects type "socks" for SOCKS5 outbounds.
        out = {
            "type": "socks",
            **base,
            "username": proxy.uuid if proxy.uuid else "",
            "password": str(proxy.details.get("password", "")),
            "version": "5",
        }

    elif proxy.protocol == "socks4":
        # [FIX] Add SOCKS4 support - sing-box supports via version parameter
        out = {
            "type": "socks",
            **base,
            "version": "4",
        }

    elif proxy.protocol == "naive":
        # [FIX] Add NaiveProxy support - sing-box has native "naive" type
        username = proxy.uuid or proxy.details.get("username", "")
        password = proxy.details.get("password", "")
        if not username or not password:
            logger.warning(
                f"Dropping Naive proxy missing credentials: {proxy.address}:{proxy.port}. "
                f"Source: {proxy.details.get('_source', 'unknown')}"
            )
            return None
        out = {
            "type": "naive",
            **base,
            "username": str(username),
            "password": str(password),
        }
        # Naive uses HTTP/2 over TLS by default
        if proxy.details.get("tls") or proxy.port == 443:
            out["tls"] = {
                "enabled": True,
                "server_name": str(proxy.details.get("sni", proxy.address)),
            }
    elif proxy.protocol == "wireguard":
        # [FIX] Respect existing local_address from proxy config if present
        # This preserves user-specified WireGuard IP assignments.
        # Only generate unique IP if no local_address is configured.
        existing_ip = proxy.details.get("local_address") or proxy.details.get(
            "private_ipv4"
        )

        if existing_ip:
            # Use existing IP (could be string or list)
            if isinstance(existing_ip, list):
                local_addresses = existing_ip
            else:
                local_addresses = [str(existing_ip)]
            logger.debug(
                f"Using existing local_address for WireGuard proxy {proxy.address}: {local_addresses}"
            )
        else:
            # [FIX] Generate unique local IP based on credentials, not endpoint
            # For WARP proxies, many use the same Cloudflare endpoints but different keys
            # Using 2 bytes from hash to generate a /32 IP in 172.16.0.0/16 range
            # to minimize collision probability during concurrent testing.
            # Hash the private_key or UUID to ensure uniqueness per account
            seed_key = (
                proxy.details.get("private_key")
                or proxy.uuid
                or f"{proxy.address}:{proxy.port}"
            )
            h = hashlib.sha256(str(seed_key).encode()).digest()
            octet3 = h[0]
            octet4 = h[1]
            # Ensure fourth octet is not .0 or .1 which can be special
            octet4 = max(octet4, 2)
            unique_ip = f"172.16.{octet3}.{octet4}/32"
            local_addresses = [unique_ip]

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
            "local_address": local_addresses,
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
        # [FIX] Check both allowInsecure and skip_cert_verify for consistency with Hysteria
        is_insecure = parse_bool(proxy.details.get("allowInsecure")) or parse_bool(
            proxy.details.get("skip_cert_verify")
        )

        out["tls"] = {
            "enabled": True,
            "server_name": str(proxy.details.get("sni", "")),
            "insecure": is_insecure,
            "alpn": proxy.details.get("alpn", []),
        }
        # [FIX] Check both "obfs-type" and "obfs" fields - parser stores as "obfs"
        obfs_type = proxy.details.get("obfs-type") or proxy.details.get("obfs")
        if obfs_type == "salamander":
            out["obfs"] = {
                "type": "salamander",
                "password": str(proxy.details.get("obfs-password", "")),
            }
        return out

    elif proxy.protocol == "tuic":
        # Validate UUID like VMess/VLESS
        uuid = proxy.uuid or proxy.details.get("uuid")
        if not uuid:
            logger.warning(
                f"Dropping TUIC proxy missing UUID: {proxy.address}:{proxy.port}"
            )
            return None
        out = {
            "type": "tuic",
            **base,
            "uuid": str(uuid),
            "password": str(proxy.details.get("password", "")),
            # [FIX] Changed 'congestion_controller' to 'congestion_control' for sing-box standard
            "congestion_control": str(
                proxy.details.get("congestion_controller", "bbr")
            ),
        }
        # [FIX] Check both allowInsecure and skip_cert_verify for consistency with Hysteria
        is_insecure = parse_bool(proxy.details.get("allowInsecure")) or parse_bool(
            proxy.details.get("skip_cert_verify")
        )

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
        # Mask all sensitive credential fields
        sensitive_fields = {
            "private_key",
            "password",
            "auth_str",
            "obfs-password",
            "pbk",
            "uuid",
            "id",
        }
        for field in sensitive_fields:
            if field in details_to_log:
                details_to_log[field] = "[MASKED]"

        # Known unsupported protocols in Sing-box (native) or require special handling
        # - SSR: Sing-box dropped support for ShadowsocksR
        # - Snell: Surge-proprietary protocol, not supported
        # - Brook: Third-party protocol, not supported
        # - Juicity: Separate project with custom client
        # - XRay: Protocol name - actual proxies should be parsed as vless/vmess
        # - OpenVPN: Sing-box supports it but requires extracted fields, not raw config
        # - V2Ray JSON: Format, not protocol - should be extracted to specific types
        if proxy.protocol in [
            "ssr",
            "snell",
            "brook",
            "juicity",
            "xray",
            "openvpn",
            "v2ray",
        ]:
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
