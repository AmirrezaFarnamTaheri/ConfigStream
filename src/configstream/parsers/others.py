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
from urllib.parse import parse_qs, quote, unquote, urlparse
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


def _quote_wireguard_userinfo(config: str) -> str:
    """Protect raw Base64 userinfo from URL parsers treating '/' as a path."""
    scheme_sep = config.find("://")
    if scheme_sep < 0:
        return config

    rest = config[scheme_sep + 3 :]
    cuts = [index for marker in ("?", "#") if (index := rest.find(marker)) >= 0]
    cut = min(cuts) if cuts else len(rest)
    authority = rest[:cut]
    if "@" not in authority:
        return config

    credential, endpoint = authority.rsplit("@", 1)
    if not credential or not endpoint:
        return config

    # '%' stays safe so already-percent-encoded keys are not double encoded.
    encoded = quote(credential, safe="%")
    return config[: scheme_sep + 3] + encoded + "@" + endpoint + rest[cut:]


def _parse_url_scheme(config: str, protocol: str, default_port: int) -> Optional[Proxy]:
    try:
        # Clean config
        config = config.strip()

        # Enforce MAX_CONFIG_LINE_LENGTH
        if MAX_CONFIG_LINE_LENGTH > 0 and len(config) > MAX_CONFIG_LINE_LENGTH:
            return None

        source_config = config
        if protocol in {"wireguard", "wg"} or config.lower().startswith("exclave://"):
            config = _quote_wireguard_userinfo(config)

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
        port = parsed.port if parsed.port is not None else default_port
        if not (1 <= port <= 65535):
            return None

        details = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        # Capture password if present (standard URL parsing)
        if parsed.password:
            details["password"] = unquote(parsed.password)

        # Special handling for username as uuid or private_key
        cred = unquote(parsed.username or "")

        proxy = Proxy(
            config=source_config,
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
            proxy.details.setdefault("password", cred)
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

    # Reparse the query specifically for WireGuard so common aliases and
    # repeated address parameters survive the generic single-value URL helper.
    repaired = _quote_wireguard_userinfo(c.strip())
    parsed_wireguard = urlparse(repaired)
    raw_params = parse_qs(parsed_wireguard.query, keep_blank_values=True)
    params = {str(key).lower(): values for key, values in raw_params.items()}

    peer_key = ""
    for alias in ("peer_public_key", "publickey", "public_key", "public-key"):
        values = params.get(alias)
        if values:
            peer_key = str(values[0]).strip().replace(" ", "+")
            if peer_key:
                break
    if peer_key:
        proxy.details["peer_public_key"] = peer_key

    psk = ""
    for alias in ("pre_shared_key", "presharedkey", "pre-shared-key"):
        values = params.get(alias)
        if values:
            psk = str(values[0]).strip().replace(" ", "+")
            if psk:
                break
    if psk:
        proxy.details["pre_shared_key"] = psk

    allowed_values: list[str] = []
    for alias in ("allowed_ips", "allowedips", "allowed-ips"):
        for raw in params.get(alias, []):
            allowed_values.extend(
                item.strip() for item in str(raw).split(",") if item.strip()
            )
    if allowed_values:
        proxy.details["allowed_ips"] = list(dict.fromkeys(allowed_values))

    if proxy.address != "wg":
        local_addresses: list[str] = []
        for raw in params.get("address", []):
            local_addresses.extend(
                item.strip()
                for item in str(raw).split(",")
                if item.strip() and "/" in item
            )
        if local_addresses:
            proxy.details["local_address"] = list(dict.fromkeys(local_addresses))

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
                logger.debug("WireGuard %s is missing.", safe_log_text(name))
                return False

            key_clean = unquote(key).strip().replace(" ", "+")
            if len(key_clean) == 64 and all(
                char in "0123456789abcdefABCDEF" for char in key_clean
            ):
                return True

            normalized = key_clean.replace("-", "+").replace("_", "/")
            normalized += "=" * ((4 - len(normalized) % 4) % 4)
            try:
                decoded = base64.b64decode(normalized, validate=True)
            except (binascii.Error, ValueError):
                logger.debug("WireGuard %s is not valid Base64.", safe_log_text(name))
                return False
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

        peer_pub = proxy.details.get("peer_public_key")
        if not isinstance(peer_pub, str) or not validate_wg_key(
            peer_pub, "peer_public_key"
        ):
            logger.debug("Dropping WireGuard proxy missing/invalid peer_public_key")
            return None
        proxy.details["peer_public_key"] = peer_pub.strip().replace(" ", "+")

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

    # Reserved bytes are optional, but when present must normalize to
    # exactly three bytes so downstream adapters do not silently discard them.
    reserved = proxy.details.get("reserved")
    if reserved not in (None, "", []):
        normalized_reserved: list[int] | None = None
        if isinstance(reserved, list):
            if len(reserved) == 3 and all(
                isinstance(item, int)
                and not isinstance(item, bool)
                and 0 <= item <= 255
                for item in reserved
            ):
                normalized_reserved = list(reserved)
        elif isinstance(reserved, str):
            text = reserved.strip()
            csv_text = (
                text[1:-1] if text.startswith("[") and text.endswith("]") else text
            )
            if _RESERVED_CSV_RE.fullmatch(csv_text):
                try:
                    reserved_values: list[int] = [
                        int(item.strip()) for item in csv_text.split(",")
                    ]
                except ValueError:
                    reserved_values = []
                if len(reserved_values) == 3 and all(
                    0 <= item <= 255 for item in reserved_values
                ):
                    normalized_reserved = reserved_values
            if normalized_reserved is None:
                encoded = text.replace("-", "+").replace("_", "/")
                encoded += "=" * ((4 - len(encoded) % 4) % 4)
                try:
                    raw_reserved = base64.b64decode(encoded, validate=True)
                except (binascii.Error, ValueError):
                    raw_reserved = b""
                if len(raw_reserved) == 3:
                    normalized_reserved = list(raw_reserved)

        if normalized_reserved is None:
            logger.debug("Dropping WireGuard proxy with invalid reserved bytes")
            return None
        proxy.details["reserved"] = normalized_reserved

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
            proxy.details["password"] = unquote(parsed.password)

    return proxy
