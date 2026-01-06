# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import re

# pylint: disable=no-member
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse
from ..models import Proxy
from .base import normalize_proxy_details
from .decoders import safe_b64_decode
from ..constants import MAX_CONFIG_LINE_LENGTH

logger = logging.getLogger(__name__)


def _parse_url_scheme(config: str, protocol: str, default_port: int) -> Optional[Proxy]:
    try:
        # Clean config
        config = config.strip()

        # Enforce MAX_CONFIG_LINE_LENGTH
        if len(config) > MAX_CONFIG_LINE_LENGTH:
            return None

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

        # Capture password if present (standard URL parsing)
        if parsed.password:
            details["password"] = parsed.password

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
        logger.debug(f"Failed to parse {protocol.upper()}: {e}")
        return None


def parse_hysteria(c: str) -> Optional[Proxy]:
    return _parse_url_scheme(c, "hysteria", 443)


def parse_hysteria2(c: str) -> Optional[Proxy]:
    # Support both hysteria2:// and hy2://
    proxy = _parse_url_scheme(c, "hysteria2", 443)
    if not proxy and c.lower().startswith("hy2://"):
        proxy = _parse_url_scheme(c, "hy2", 443)
        if proxy:
            proxy.protocol = "hysteria2"  # Normalize protocol

    if proxy:
        # [FIX] Normalize parameter aliases
        # Map obfs_password / obfsPassword -> obfs-password
        if "obfs-password" not in proxy.details:
            # Check for aliases in a consistent order of preference
            if "obfs_password" in proxy.details:
                proxy.details["obfs-password"] = proxy.details.pop("obfs_password")
            elif "obfsPassword" in proxy.details:
                proxy.details["obfs-password"] = proxy.details.pop("obfsPassword")

        # Hysteria 2 Obfuscation & Masquerading
        # 'obfs' -> type (e.g., 'salamander'), 'obfs-password' -> password
        if "obfs" in proxy.details:
            obfs_type = proxy.details["obfs"]
            if obfs_type not in ["salamander", "none"]:
                logger.debug(f"Unknown Hysteria2 obfs type: {obfs_type}")

            # Validate obfs-password presence if obfs is set
            if obfs_type == "salamander" and "obfs-password" not in proxy.details:
                logger.debug(
                    "Hysteria2 obfs=salamander requires obfs-password. Dropping invalid proxy."
                )
                return None

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
            # If no password, Hysteria2 is only valid if the server allows anonymous access.
            logger.debug(
                "Hysteria2 config missing password (UUID field) - assuming anonymous auth."
            )

    return proxy


def parse_tuic(c: str) -> Optional[Proxy]:
    # TUIC v5 support
    proxy = _parse_url_scheme(c, "tuic", 443)
    if proxy:
        # [FIX] TUIC often requires both UUID and Password.
        # _parse_url_scheme puts user -> uuid, pass -> details['password']
        # If uuid is present but password is missing, some clients use uuid as password.
        if proxy.uuid and "password" not in proxy.details:
            # Use UUID as password if password is missing
            proxy.details["password"] = proxy.uuid

        # Ensure ALPN is present for TUIC (mandatory for some versions)
        if "alpn" not in proxy.details:
            proxy.details["alpn"] = ["h3"]
    return proxy


def parse_wireguard(c: str) -> Optional[Proxy]:
    proxy = _parse_url_scheme(c, "wireguard", 51820)
    if not proxy and c.lower().startswith("wg://"):
        proxy = _parse_url_scheme(c, "wg", 51820)
        if proxy:
            proxy.protocol = "wireguard"  # Normalize

    if not proxy:
        return None

    # WireGuard specific: if private_key is not in details, try to use uuid (username)
    if "private_key" not in proxy.details:
        if proxy.uuid:
            proxy.details["private_key"] = proxy.uuid
        elif "private-key" in proxy.details:
            proxy.details["private_key"] = proxy.details.pop("private-key")
        elif "privateKey" in proxy.details:
            proxy.details["private_key"] = proxy.details.pop("privateKey")
        else:
            # [FIX] Enforce private_key check
            logger.debug("Dropping WireGuard proxy missing private_key")
            return None

    private_key = proxy.details.get("private_key")
    if not private_key:
        logger.debug("WireGuard config missing private_key.")
        return None

    # [FIX] Validate WireGuard Private Key Length (Must be 32 bytes)
    # The Go Tester fails with "IPC error -22: hex string does not fit the slice" if length is wrong
    try:
        # Standard WG keys are Base64 encoded
        # We try to decode it. If it fails or length is not 32 bytes, we drop it.
        # Note: safe_b64_decode returns string (utf-8), but keys are binary.
        # We need raw bytes check. So we use standard b64decode here or check string length.
        # A 32-byte key in Base64 is approx 44 chars (43 chars + padding).
        pk_clean = private_key.strip().replace(" ", "+")  # Some configs have spaces

        # Heuristic length check first
        if len(pk_clean) < 40 or len(pk_clean) > 50:
             # Check if it's hex (64 chars)
             if len(pk_clean) == 64 and all(c in "0123456789abcdefABCDEF" for c in pk_clean):
                 pass # Hex is valid for some implementations, pass it through
             else:
                 logger.debug(f"WireGuard private_key length invalid ({len(pk_clean)}): {pk_clean[:10]}...")
                 return None

        # Verify decoding if it looks like Base64
        if len(pk_clean) >= 40 and len(pk_clean) <= 50:
             import base64
             import binascii
             # Pad if needed
             pad = len(pk_clean) % 4
             if pad:
                 pk_clean += "=" * (4 - pad)

             decoded = base64.b64decode(pk_clean, validate=False)
             if len(decoded) != 32:
                 logger.debug(f"WireGuard private_key decoded length mismatch ({len(decoded)} != 32).")
                 return None

    except Exception as e:
        logger.debug(f"WireGuard private_key validation failed: {e}")
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
                logger.warning(
                    f"Invalid reserved bytes format for WireGuard: {reserved}. Removing invalid field."
                )
                del proxy.details["reserved"]
            elif (
                len(reserved) > 128
            ):  # Enforce max length (standard key is 32 bytes/44 chars b64)
                logger.warning(f"Reserved bytes too long: {len(reserved)}")
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
        # Validate host matches strict regex (IP or Domain) to avoid injection
        if not re.match(r"^[a-zA-Z0-9\.\-\_]+$", proxy.address):
            logger.warning(f"Invalid SSH hostname: {proxy.address}")
            return None

        # SSH Tunnels: Parse credentials
        parsed = urlparse(config)
        if parsed.password:
            proxy.details["password"] = parsed.password

    return proxy
