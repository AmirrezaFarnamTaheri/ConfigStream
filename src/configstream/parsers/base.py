"""
Base parsing utilities and constants.
"""

import base64
import binascii
import logging
from typing import Optional, List

from ..constants import (
    MAX_B64_INPUT_SIZE,
    MAX_B64_OUTPUT_SIZE,
    MAX_CONFIG_LINE_LENGTH,
    MAX_LINES_PER_SOURCE,
    VALID_PROTOCOLS,
)
from ..models import Proxy

logger = logging.getLogger(__name__)

VALID_B64_CHARS = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r \t"
)


def validate_b64_input(data: str) -> Optional[str]:
    """Validate base64 string before attempting decode."""
    if not isinstance(data, str):
        logger.warning("Expected string, got %s", type(data).__name__)
        return None

    trimmed = data.strip()
    if not trimmed:
        logger.debug("Empty base64 input")
        return None

    if len(trimmed) > MAX_B64_INPUT_SIZE:
        logger.error(
            "Base64 input too large: %s bytes (max: %s)",
            len(trimmed),
            MAX_B64_INPUT_SIZE,
        )
        return None

    invalid_chars = set(trimmed) - VALID_B64_CHARS
    if invalid_chars:
        logger.warning("Invalid base64 characters: %s", invalid_chars)
        return None

    cleaned = "".join(c for c in trimmed if c not in " \n\r\t")
    padding_needed = (4 - len(cleaned) % 4) % 4
    if padding_needed > 0:
        cleaned += "=" * padding_needed

    return cleaned


def safe_b64_decode(data: str) -> str:
    """Safely decode base64 with comprehensive validation.

    NOTE: We perform a fast size check *before* any heavy processing to
    avoid memory pressure on extremely large payloads.
    """
    # Fast path: reject obviously oversized input before validation/decoding.
    if isinstance(data, str) and len(data) > MAX_B64_INPUT_SIZE:
        logger.error(
            "Base64 input too large: %s bytes (max: %s) – skipping decode",
            len(data),
            MAX_B64_INPUT_SIZE,
        )
        return data

    validated = validate_b64_input(data)
    if validated is None:
        return data

    try:
        decoded_bytes = base64.b64decode(validated, validate=True)

        if len(decoded_bytes) > MAX_B64_OUTPUT_SIZE:
            logger.error(
                f"Decoded output too large: {len(decoded_bytes)} bytes (max: {MAX_B64_OUTPUT_SIZE})"
            )
            return data

        try:
            return decoded_bytes.decode("utf-8")
        except UnicodeDecodeError:
            logger.debug("Decoded data is not valid UTF-8, trying latin-1")
            return decoded_bytes.decode("latin-1")
    except (binascii.Error, ValueError) as exc:
        logger.warning("Base64 decode failed: %s", exc)
        return data
    except MemoryError:
        logger.error("Out of memory decoding base64")
        return data
    except Exception as exc:
        logger.error("Unexpected error decoding base64: %s", exc)
        return data


def is_plausible_proxy_config(config: str) -> bool:
    """Basic plausibility check for proxy configuration."""
    # OpenVPN support
    if config.startswith("-----BEGIN CERTIFICATE"):
        return True
    if "client" in config and ("dev tun" in config or "dev tap" in config):
        # It's likely an OVPN file content, which is handled separately
        return True

    if "://" not in config:
        return False
    protocol, rest = config.split("://", 1)
    if len(protocol) > 20 or len(rest) < 4:
        return False
    special_char_count = sum(
        1 for c in rest if not c.isalnum() and c not in ":-_./@#%?&="
    )
    if special_char_count > len(rest) * 0.5:
        return False
    return True


def extract_config_lines(
    payload: str, max_lines: int = MAX_LINES_PER_SOURCE
) -> List[str]:
    """Extract configuration lines with validation and limits."""
    if not isinstance(payload, str) or not payload.strip():
        return []

    # Check if it's an OpenVPN file
    if "client" in payload and ("dev tun" in payload or "dev tap" in payload):
        # Treat the whole payload as one config
        if len(payload) < MAX_B64_OUTPUT_SIZE:  # Size limit check
            return [payload]

    lines = payload.splitlines()
    if len(lines) > max_lines:
        logger.warning("Payload has %s lines, truncating to %s", len(lines), max_lines)
        lines = lines[:max_lines]

    valid_prefixes = {p for p in VALID_PROTOCOLS if not p.endswith("://")}
    valid_prefixes.update({p + "://" for p in VALID_PROTOCOLS})

    configs = []
    for line in lines:
        candidate = line.strip()
        if (
            not candidate
            or candidate.startswith("#")
            or len(candidate) > MAX_CONFIG_LINE_LENGTH
        ):
            continue

        parts = candidate.split("://", 1)
        if len(parts) == 2:
            protocol = parts[0]
            if protocol in valid_prefixes and is_plausible_proxy_config(candidate):
                configs.append(candidate)
    return configs


def normalize_proxy_details(proxy: Proxy) -> None:
    """
    Standardizes common proxy attributes (sni, path, etc.) from the
    protocol-specific `details` dictionary into top-level keys for easier access
    and deduplication. This mutates the proxy object.
    """
    if not proxy.details:
        return

    # 1. Standardize SNI (Server Name Indication) / Host
    # Order of precedence: 'sni' > 'peer' > 'host' (from details)
    sni = (
        proxy.details.get("sni")
        or proxy.details.get("peer")
        or proxy.details.get("host")
    )
    if sni:
        proxy.details["sni"] = str(sni)

    # For VMess, SNI might be in headers which is a dict. This should take
    # precedence over the 'host' field.
    if proxy.protocol == "vmess":
        headers = proxy.details.get("headers")
        if isinstance(headers, dict) and "Host" in headers:
            proxy.details["sni"] = headers["Host"]

    # For Shadowsocks, SNI can be in plugin opts
    if proxy.protocol == "shadowsocks" and "plugin" in proxy.details:
        plugin_str = proxy.details.get("plugin", "")
        if isinstance(plugin_str, str):
            plugin_opts = dict(
                item.split("=") for item in plugin_str.split(";") if "=" in item
            )
            if "obfs-host" in plugin_opts:
                proxy.details.setdefault("sni", plugin_opts["obfs-host"])
            if "obfs-uri" in plugin_opts:
                proxy.details.setdefault("path", plugin_opts["obfs-uri"])

    # 2. Standardize Path
    # Order of precedence: 'path' > 'serviceName'
    path = proxy.details.get("path") or proxy.details.get("serviceName")
    if path:
        proxy.details["path"] = str(path)

    # 3. Standardize ALPN (Application-Layer Protocol Negotiation)
    alpn = proxy.details.get("alpn")
    if alpn:
        if isinstance(alpn, str):
            # Can be comma-separated
            alpn_list = [s.strip() for s in alpn.split(",")]
            proxy.details["alpn"] = alpn_list
        elif isinstance(alpn, (list, tuple)):
            proxy.details["alpn"] = [str(item) for item in alpn]
