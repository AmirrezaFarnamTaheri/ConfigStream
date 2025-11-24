import logging
import re
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse
from ..models import Proxy
from .base import normalize_proxy_details

logger = logging.getLogger(__name__)


def _parse_url_scheme(config: str, protocol: str, default_port: int) -> Optional[Proxy]:
    try:
        # Clean config
        config = config.strip()
        parsed = urlparse(config)

        # Handle scheme mismatch or missing scheme
        if parsed.scheme:
            if parsed.scheme.lower() not in (protocol, protocol.lower()):
                # If scheme mismatches (e.g. hysteria2:// in a hysteria parser), return None
                # This allows specific parsers to own their protocols
                return None
        else:
            # If scheme is missing but config starts with expected protocol,
            # likely urlparse failed to split correctly (rare) or malformed.
            if config.lower().startswith(f"{protocol}://"):
                # Try to manually split if urlparse failed oddly
                # For now, we assume if urlparse failed to see scheme, it's invalid
                return None

            # If no scheme and doesn't start with protocol, it's not for us
            return None

        if not parsed.hostname or len(parsed.hostname) > 255:
            return None
        port = parsed.port or default_port
        if not (1 <= port <= 65535):
            return None

        details = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        # Special handling for username as uuid or private_key
        uuid = parsed.username or ""

        proxy = Proxy(
            config=config,
            protocol=protocol,
            address=parsed.hostname,
            port=port,
            uuid=uuid,
            remarks=unquote(parsed.fragment or "")[:200],
            details=details,
        )
        normalize_proxy_details(proxy)
        return proxy
    except (ValueError, IndexError) as e:
        logger.debug("Failed to parse %s: %s", protocol.upper(), e)
        return None


def parse_hysteria(c: str) -> Optional[Proxy]:
    return _parse_url_scheme(c, "hysteria", 443)


def parse_hysteria2(c: str) -> Optional[Proxy]:
    proxy = _parse_url_scheme(c, "hysteria2", 443)
    if proxy:
        # Hysteria 2 Obfuscation & Masquerading
        # 'obfs' -> type (e.g., 'salamander'), 'obfs-password' -> password
        if "obfs" in proxy.details:
            obfs_type = proxy.details["obfs"]
            if obfs_type not in ["salamander", "none"]:
                logger.debug(f"Unknown Hysteria2 obfs type: {obfs_type}")

            # Validate obfs-password presence if obfs is set
            if obfs_type == "salamander" and "obfs-password" not in proxy.details:
                logger.debug("Hysteria2 obfs=salamander requires obfs-password")
                # We can either drop it or keep it (it might fail later).
                # Let's keep it but log warning.

        # Port Hopping (Advanced)
        # Format: ports=80,443,8000-9000
        if "ports" in proxy.details:
            # Validate format
            ports_val = proxy.details["ports"]
            if not re.match(r"^[\d,\-]+$", ports_val):
                logger.warning(f"Invalid port hopping format: {ports_val}")
                del proxy.details["ports"]

        if not proxy.uuid:
            # Auth is optional in some cases but usually required.
            # If no password, Hysteria2 might fail unless server allows anonymous (rare).
            # We treat it as valid but suspect.
            logger.debug("Hysteria2 config missing password (UUID field).")

    return proxy


def parse_tuic(c: str) -> Optional[Proxy]:
    # TUIC v5 support
    return _parse_url_scheme(c, "tuic", 443)


def parse_wireguard(c: str) -> Optional[Proxy]:
    proxy = _parse_url_scheme(c, "wireguard", 51820)
    if not proxy:
        return None

    # WireGuard specific: if private_key is not in details, try to use uuid (username)
    if "private_key" not in proxy.details:
        if proxy.uuid:
            proxy.details["private_key"] = proxy.uuid
        else:
            logger.debug("WireGuard config missing private_key.")
            return None

    if not proxy.details.get("private_key"):
        logger.debug("WireGuard config missing private_key.")
        return None

    # Reserved bytes check (for WARP/WireGuard)
    reserved = proxy.details.get("reserved")
    if reserved:
        if isinstance(reserved, str):
            # Validate format [x, y, z] or base64
            # Support [1,2,3], 1,2,3 and base64
            is_bracketed = re.match(r"^\[[\d\s,]+\]$", reserved)
            is_csv = re.match(r"^[\d\s,]+$", reserved)
            is_b64 = re.match(r"^[a-zA-Z0-9+/=]+$", reserved)

            if not (is_bracketed or is_csv or is_b64):
                logger.debug(f"Invalid reserved bytes format for WireGuard: {reserved}")
                # If invalid format, we might choose to drop it or clear it.
                # For safety, let's clear it to avoid breaking clients
                del proxy.details["reserved"]
        else:
            # If it's not a string (e.g. list from some internal process), assume valid if it's a list of ints
            if not (
                isinstance(reserved, list) and all(isinstance(x, int) for x in reserved)
            ):
                logger.debug(
                    f"Invalid reserved bytes type for WireGuard: {type(reserved)}"
                )
                del proxy.details["reserved"]

    return proxy


def parse_xray(c: str) -> Optional[Proxy]:
    proxy = _parse_url_scheme(c, "xray", 443)
    if not proxy or not proxy.uuid:
        logger.debug("XRay config missing UUID.")
        return None
    return proxy


def parse_snell(c: str) -> Optional[Proxy]:
    """Parse Snell proxy configuration."""
    return _parse_url_scheme(c, "snell", 443)


def parse_brook(c: str) -> Optional[Proxy]:
    """Parse Brook proxy configuration."""
    return _parse_url_scheme(c, "brook", 9999)


def parse_juicity(c: str) -> Optional[Proxy]:
    """Parse Juicity proxy configuration."""
    proxy = _parse_url_scheme(c, "juicity", 443)
    if proxy and not proxy.uuid:
        logger.debug("Juicity config missing UUID.")
        return None
    return proxy


def parse_ssh(config: str) -> Optional[Proxy]:
    """Parse SSH proxy configuration."""
    # format: ssh://user:pass@host:port#remark
    proxy = _parse_url_scheme(config, "ssh", 22)
    if proxy:
        # SSH Tunnels: Parse credentials
        parsed = urlparse(config)
        if parsed.password:
            proxy.details["password"] = parsed.password

    return proxy
