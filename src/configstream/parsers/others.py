# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Protocol parsers: Xray, Snell, Brook, Juicity, SSH, Naive, OpenVPN, etc.

parse_xray, parse_snell, parse_brook, parse_juicity are exported and wired in auto_detect.py
for pipeline format support.
"""

import base64
import binascii
import json
import logging
import re
import uuid as uuid_lib

# pylint: disable=no-member
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse
from pydantic import ValidationError
from ..models import Proxy
from .base import normalize_proxy_details
from ..constants import MAX_CONFIG_LINE_LENGTH
from ..security_validator import SecurityValidator, safe_log_text

logger = logging.getLogger(__name__)

# Pre-compiled patterns for per-proxy parsing hot paths
_PORT_HOPPING_RE = re.compile(r"^[\d,\-]+$")
_RESERVED_BRACKETED_RE = re.compile(r"^\[[\d\s,]+\]$")
_RESERVED_CSV_RE = re.compile(r"^[\d\s,]+$")
_RESERVED_B64_RE = re.compile(r"^[a-zA-Z0-9+/=]+$")
_SSH_HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9\.\-\_]+$")


def _parse_url_scheme(config: str, protocol: str, default_port: int) -> Optional[Proxy]:
    try:
        # Clean config
        config = config.strip()

        # Enforce MAX_CONFIG_LINE_LENGTH
        if MAX_CONFIG_LINE_LENGTH > 0 and len(config) > MAX_CONFIG_LINE_LENGTH:
            return None

        parsed = urlparse(config)

        # Handle scheme mismatch or missing scheme
        if parsed.scheme:
            # Allow exclave scheme for wireguard parser
            allowed_schemes = [protocol, protocol.lower()]
            if protocol == "wireguard":
                allowed_schemes.extend(["exclave"])

            if parsed.scheme.lower() not in allowed_schemes:
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
        cred = parsed.username or ""

        proxy = Proxy(
            config=config,
            protocol=protocol,
            address=parsed.hostname,
            port=port,
            uuid=cred,
            remarks=unquote(parsed.fragment or "")[:200],
            details=details,
        )
        if cred:
            # Different protocols expect credentials in different fields
            # We'll put it in both places and let the converter sort it out
            proxy.details["password"] = cred
            proxy.details["username"] = cred
        normalize_proxy_details(proxy)
        return proxy
    except (
        ValidationError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        TimeoutError,
        IndexError,
        TypeError,
        binascii.Error,
    ) as e:
        logger.debug(
            "Failed to parse %s: %s",
            protocol.upper(),
            safe_log_text(e),
        )
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
        proxy.details.pop("username", None)
        # Store auth/password credential in password detail field per schema
        auth_credential = (
            proxy.uuid
            or proxy.details.get("password")
            or proxy.details.pop("auth", None)
            or ""
        )
        if auth_credential:
            proxy.details["password"] = auth_credential
        proxy.details.pop("auth", None)

        # Keep non-UUID credentials out of proxy.uuid
        if not SecurityValidator.is_valid_uuid(proxy.uuid):
            proxy.uuid = str(uuid_lib.uuid4())

        # Normalize parameter aliases
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
                logger.debug(
                    "Unknown Hysteria2 obfs type: %s",
                    safe_log_text(obfs_type),
                )

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
            if not _PORT_HOPPING_RE.match(ports_val):
                logger.warning(
                    "Invalid port hopping format: %s",
                    safe_log_text(ports_val),
                )
                del proxy.details["ports"]

        if not auth_credential:
            # Auth is optional in some cases but usually required.
            # If no password, Hysteria2 is only valid if the server allows anonymous access.
            logger.debug(
                "Hysteria2 config missing password - treating as anonymous auth."
            )

    return proxy


def parse_tuic(c: str) -> Optional[Proxy]:
    # TUIC v5 support
    proxy = _parse_url_scheme(c, "tuic", 443)
    if proxy:
        # TUIC often requires both UUID and Password.
        # _parse_url_scheme puts user -> uuid, pass -> details['password']
        # If uuid is present but password is missing, some clients use uuid as password.
        if proxy.uuid and "password" not in proxy.details:
            # Use UUID as password if password is missing
            proxy.details["password"] = proxy.uuid

        if not proxy.uuid or not proxy.details.get("password"):
            logger.debug("TUIC config missing UUID or password.")
            return None

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

    # Handle exclave:// scheme
    if not proxy and c.lower().startswith("exclave://"):
        proxy = _parse_url_scheme(
            c, "wireguard", 51820
        )  # Pass expected protocol 'wireguard', scheme check handled inside
        if proxy:
            proxy.protocol = "wireguard"

    if not proxy:
        return None

    proxy.details.pop("username", None)
    proxy.details.pop("password", None)

    # Recover real endpoint address if hostname is 'wg' or if endpoint/peer is present
    if "endpoint" in proxy.details:
        ep_val = proxy.details.pop("endpoint")
        if ":" in ep_val:
            h, p = ep_val.rsplit(":", 1)
            if p.isdigit():
                proxy.address = h.strip("[]")
                proxy.port = int(p)
            else:
                proxy.address = ep_val
        else:
            proxy.address = ep_val
    elif "peer" in proxy.details:
        peer_val = proxy.details.pop("peer")
        if ":" in peer_val:
            h, p = peer_val.rsplit(":", 1)
            if p.isdigit():
                proxy.address = h.strip("[]")
                proxy.port = int(p)
            else:
                proxy.address = peer_val
        else:
            proxy.address = peer_val
    elif proxy.address == "wg" and "address" in proxy.details:
        addr_val = proxy.details["address"]
        # Handle host:port split
        if ":" in addr_val:
            # Check if IPv6 [host]:port
            if addr_val.startswith("["):
                end_bracket = addr_val.find("]")
                if end_bracket != -1:
                    h = addr_val[1:end_bracket]
                    rest = addr_val[end_bracket + 1 :]
                    if rest.startswith(":"):
                        p = rest[1:]
                        if p.isdigit():
                            proxy.address = h
                            proxy.port = int(p)
                    else:
                        proxy.address = h
            else:
                h, p = addr_val.rsplit(":", 1)
                if p.isdigit():
                    proxy.address = h
                    proxy.port = int(p)
                else:
                    proxy.address = addr_val
        else:
            proxy.address = addr_val

    # Ensure CIDR data (e.g. 10.0.0.2/32) is moved to local_address and not kept in proxy.address
    if "address" in proxy.details:
        addr_val = proxy.details.pop("address")
        if "/" in addr_val and "local_address" not in proxy.details:
            proxy.details["local_address"] = addr_val
        elif "/" not in addr_val and proxy.address == "wg":
            proxy.address = addr_val

    if "/" in proxy.address:
        if "local_address" not in proxy.details:
            proxy.details["local_address"] = proxy.address
        logger.debug(
            "Dropping WireGuard proxy with CIDR in remote endpoint address: %s",
            safe_log_text(proxy.address),
        )
        return None

    if proxy.address == "wg":
        logger.debug("Dropping WireGuard proxy missing remote endpoint address")
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
            # Enforce private_key check
            logger.debug("Dropping WireGuard proxy missing private_key")
            return None

    # Keep non-UUID private key out of proxy.uuid
    if not SecurityValidator.is_valid_uuid(proxy.uuid):
        proxy.uuid = str(uuid_lib.uuid4())

    private_key = proxy.details.get("private_key")
    if not private_key:
        logger.debug("WireGuard config missing private_key.")
        return None

    # Validate WireGuard Keys (Must be 32 bytes)
    # The Go Tester fails with "IPC error -22: hex string does not fit the slice" if length is wrong
    # Also "failed to get peer by public key" indicates invalid peer_public_key
    try:

        def validate_wg_key(key: str, name: str) -> bool:
            if not key:
                return True  # Let later checks handle missing optional keys if any

            # Handle URL-encoded keys (e.g. %2B for +)
            if "%" in key:
                try:
                    from urllib.parse import unquote

                    key = unquote(key)
                except (ValueError, TypeError):  # nosec B110
                    logging.getLogger(__name__).debug("Suppressed unquote exception")
                    pass

            key_clean = key.strip().replace(" ", "+")

            # Heuristic length check first
            if len(key_clean) < 40 or len(key_clean) > 50:
                # Check if it's hex (64 chars)
                if len(key_clean) == 64 and all(
                    c in "0123456789abcdefABCDEF" for c in key_clean
                ):
                    return True
                else:
                    logger.debug(
                        "WireGuard %s length invalid (%d).",
                        safe_log_text(name),
                        len(key_clean),
                    )
                    return False

            # Verify decoding if it looks like Base64
            if len(key_clean) >= 40 and len(key_clean) <= 50:
                pad = len(key_clean) % 4
                if pad:
                    key_clean += "=" * (4 - pad)

                decoded = base64.b64decode(key_clean, validate=False)
                if len(decoded) != 32:
                    logger.debug(
                        "WireGuard %s decoded length mismatch (%d != 32).",
                        safe_log_text(name),
                        len(decoded),
                    )
                    return False
            return True

        if not validate_wg_key(private_key, "private_key"):
            return None

        # Also validate peer_public_key if present
        peer_pub = proxy.details.get("peer_public_key")
        if peer_pub and not validate_wg_key(peer_pub, "peer_public_key"):
            return None

    except (
        ValidationError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        TimeoutError,
        IndexError,
        TypeError,
        binascii.Error,
    ) as e:
        logger.debug("WireGuard key validation failed: %s", safe_log_text(e))
        return None

    # Reserved bytes check (for WARP/WireGuard)
    reserved = proxy.details.get("reserved")
    if reserved:
        if isinstance(reserved, str):
            # Validate format [x, y, z] or base64
            # Support [1,2,3], 1,2,3 and base64
            is_bracketed = _RESERVED_BRACKETED_RE.match(reserved)
            is_csv = _RESERVED_CSV_RE.match(reserved)
            is_b64 = _RESERVED_B64_RE.match(reserved)

            if not (is_bracketed or is_csv or is_b64):
                logger.warning(
                    "Invalid reserved bytes format for WireGuard: %s. Removing invalid field.",
                    safe_log_text(reserved),
                )
                del proxy.details["reserved"]
            elif (
                len(reserved) > 128
            ):  # Enforce max length (standard key is 32 bytes/44 chars b64)
                logger.warning("Reserved bytes too long: %d", len(reserved))
                del proxy.details["reserved"]
        else:
            # If it's not a string (e.g. list from some internal process), assume valid if it's a list of ints
            if not (
                isinstance(reserved, list) and all(isinstance(x, int) for x in reserved)
            ):
                logger.debug(
                    "Invalid reserved bytes type for WireGuard: %s",
                    safe_log_text(type(reserved)),
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
    proxy = _parse_url_scheme(c, "snell", 443)
    if proxy and not (proxy.uuid or proxy.details.get("password")):
        logger.debug("Snell config missing password.")
        return None
    return proxy


def parse_brook(c: str) -> Optional[Proxy]:
    """Parse Brook proxy configuration."""
    proxy = _parse_url_scheme(c, "brook", 9999)
    if proxy and not (proxy.uuid or proxy.details.get("password")):
        logger.debug("Brook config missing password.")
        return None
    return proxy


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
        if not proxy.uuid:
            logger.debug("SSH config missing username.")
            return None

        # Validate host matches strict regex (IP or Domain) to avoid injection
        if not _SSH_HOSTNAME_RE.match(proxy.address):
            logger.warning(
                "Invalid SSH hostname: %s",
                safe_log_text(proxy.address),
            )
            return None

        # SSH Tunnels: Parse credentials
        parsed = urlparse(config)
        if parsed.password:
            proxy.details["password"] = parsed.password

    return proxy
