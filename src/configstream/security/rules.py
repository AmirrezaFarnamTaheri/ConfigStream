"""
Security validation rules for proxy configurations.
"""

import re
import logging
from typing import Dict, FrozenSet, Optional

from configstream.config import AppSettings
from configstream.constants import (
    DANGEROUS_PORTS,
    SUSPICIOUS_DOMAINS,
    MAX_PORT,
    VALID_PROTOCOLS,
    MAX_CONFIG_LINE_LENGTH,
)

logger = logging.getLogger(__name__)

# Security issue categories
SECURITY_CATEGORIES = {
    "PORT_UNSAFE": "port_security",
    "ADDRESS_PRIVATE": "address_private_ip",
    "ADDRESS_SUSPICIOUS": "address_suspicious",
    "ADDRESS_BLOCKED": "address_blocked",
    "PROTOCOL_UNKNOWN": "protocol_invalid",
    "CONFIG_TOO_LONG": "suspicious_config_format",
    "CONFIG_NULL_BYTE": "suspicious_config_malformed",
    "HONEYPOT_SUSPECTED": "honeypot_suspected",
    "UUID_INVALID": "config_uuid_invalid",
}

# Cache AppSettings instance
_APP_SETTINGS_CACHE = AppSettings()


def validate_port(port: int) -> Optional[str]:
    """Check if port is safe and return issue if not."""
    if port < 1 or port > MAX_PORT:
        return f"Port out of valid range (1-{MAX_PORT}): {port}"
    if port in DANGEROUS_PORTS:
        # Sample log to avoid spam
        if logger.isEnabledFor(logging.DEBUG):
            logger.warning(f"Dangerous port detected: {port}")
        else:
            # We don't log individual dangerous ports at INFO/WARNING to avoid spam,
            # assuming the validator summary handles it.
            # Or use a sampling mechanism if necessary.
            pass
        return f"Dangerous port: {port}"
    return None


def validate_address(
    address: str, suspicious_domain_allowlist: FrozenSet[str]
) -> Dict[str, str]:
    """Check address safety and return categorized issues."""
    issues = {}

    if not address:
        issues[SECURITY_CATEGORIES["ADDRESS_SUSPICIOUS"]] = "Empty address"
        return issues

    address_lower = address.lower()

    # Allow bypass for reserved or test-specific domains
    if address_lower in suspicious_domain_allowlist or address_lower.endswith(".test"):
        return issues

    # [FIX] Normalize IDN and unicode
    try:
        import idna
        import unicodedata

        normalized = unicodedata.normalize("NFKC", address_lower)
        encoded = idna.encode(normalized).decode("ascii")
        address_check = encoded
    except Exception:
        address_check = address_lower

    # Check for suspicious patterns (exact or subdomain match)
    for suspicious in SUSPICIOUS_DOMAINS:
        if address_check == suspicious or address_check.endswith("." + suspicious):
            logger.warning(f"Suspicious address pattern found: {address}")
            issues[SECURITY_CATEGORIES["ADDRESS_SUSPICIOUS"]] = (
                f"Suspicious address pattern: {address}"
            )
            return issues

    # DNS rebinding / localhost evasion protection
    # 1) Hex or octal IPv4 notations that can map to localhost or private ranges.
    if address_lower.startswith("0x"):
        # Exclude valid domains that happen to start with 0x (like 0xerfan.github.io)
        if "." in address_lower:
            # This looks like a domain name, not hex IP
            # Only flag if it looks like an actual hex IP address
            parts = address_lower.split(".")
            if not all(p.startswith("0x") or p.isdigit() for p in parts):
                # It's a normal domain, not a hex-encoded IP - allow it
                return issues
            else:
                logger.warning(
                    f"Non-standard IP notation (possible DNS rebinding): {address}"
                )
                issues[SECURITY_CATEGORIES["ADDRESS_SUSPICIOUS"]] = (
                    f"Non-standard notation: {address}"
                )
                return issues
        else:
            logger.warning(
                f"Non-standard IP notation (possible DNS rebinding): {address}"
            )
            issues[SECURITY_CATEGORIES["ADDRESS_SUSPICIOUS"]] = (
                f"Non-standard notation: {address}"
            )
            return issues
    elif re.match(r"^0[0-7]{1,11}\.", address_lower):
        # Only flag as octal/ambiguous if it looks like an IP structure (digits and dots),
        # not a hostname starting with digits (e.g. 026.worker.dev).
        is_ip_structure = re.match(r"^[\d\.]+$", address_lower)
        if is_ip_structure:
            logger.warning(
                f"Non-standard IP notation (possible DNS rebinding): {address}"
            )
            issues[SECURITY_CATEGORIES["ADDRESS_SUSPICIOUS"]] = (
                f"Non-standard notation: {address}"
            )
            return issues

    # 2) URL-encoded localhost / 127.0.0.1 variants
    #    e.g. %31%32%37%2E%30%2E%30%2E%31
    if "%" in address_lower:
        try:
            from urllib.parse import unquote

            decoded = unquote(address_lower)
            if decoded.startswith("127.") or decoded in ("localhost", "::1"):
                logger.warning(
                    f"URL-encoded localhost/loopback detected: {address} -> {decoded}"
                )
                issues[SECURITY_CATEGORIES["ADDRESS_PRIVATE"]] = (
                    f"Encoded loopback address: {decoded}"
                )
                return issues
        except Exception as e:
            # If decoding fails we just fall back to normal checks
            logger.debug(f"Failed to URL-decode address {address}: {e}")

    # 3) IPv6 loopback / IPv4-mapped loopback
    if address_lower in ("::1", "0:0:0:0:0:0:0:1") or address_lower.startswith(
        "::ffff:127."
    ):
        logger.warning(f"Loopback IPv6 or IPv4-mapped localhost detected: {address}")
        issues[SECURITY_CATEGORIES["ADDRESS_PRIVATE"]] = f"Loopback address: {address}"
        return issues

    # Combined check for private, reserved, and special-use addresses
    if not _APP_SETTINGS_CACHE.ALLOW_PRIVATE_IPS:
        # Check if address looks like an IP (IPv4 or IPv6) before applying IP rules
        # This prevents blocking domains that start with numbers like 10.example.com
        is_ip_match = re.match(r"^[\d\.:]+$", address_lower)
        is_localhost = address_lower == "localhost"

        if is_ip_match or is_localhost:
            special_address_patterns = [
                # Loopback
                r"^127\.",
                r"^::1$",
                r"^localhost$",
                # Private ranges
                r"^10\.",
                r"^172\.(1[6-9]|2[0-9]|3[0-1])\.",
                r"^192\.168\.",
                # Link-local
                r"^169\.254\.",
                r"^fe80:",
                # Unique local
                r"^fc00:",
                r"^fd00:",
                # Unspecified
                r"^0\.0\.0\.0$",
                r"^0\.",  # "This network"
                # Broadcast
                r"^255\.255\.255\.255$",
            ]

            for pattern in special_address_patterns:
                if re.match(pattern, address_lower):
                    logger.warning(f"Special or private address detected: {address}")
                    issues[SECURITY_CATEGORIES["ADDRESS_PRIVATE"]] = (
                        f"Special address: {address}"
                    )
                    return issues

    return issues


def validate_protocol(protocol: str) -> Optional[str]:
    """Validate protocol is recognized."""
    if protocol.lower() not in VALID_PROTOCOLS:
        logger.warning(f"Unknown protocol detected: {protocol}")
        return f"Unknown protocol: {protocol}"
    return None


def validate_config_string(config: str) -> Dict[str, str]:
    """Check config string for injection attempts and return categorized issues."""
    issues = {}

    if not config:
        issues[SECURITY_CATEGORIES["CONFIG_TOO_LONG"]] = "Suspicious: Empty config"
        return issues

    # Check for null bytes
    if "\x00" in config:
        logger.error("Null byte detected in config")
        issues[SECURITY_CATEGORIES["CONFIG_NULL_BYTE"]] = (
            "Suspicious: Contains null byte"
        )
        return issues

    # Check length
    if len(config) > MAX_CONFIG_LINE_LENGTH:
        logger.warning(f"Config too long: {len(config)} chars")
        issues[SECURITY_CATEGORIES["CONFIG_TOO_LONG"]] = (
            f"Config exceeds max length: {len(config)} chars"
        )
        return issues

    return issues
