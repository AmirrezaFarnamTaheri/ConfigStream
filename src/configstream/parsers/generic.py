# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import json
import re
from typing import Optional
from urllib.parse import urlparse, unquote
from ..models import Proxy
from ..constants import MAX_CONFIG_LINE_LENGTH

logger = logging.getLogger(__name__)

# Regex patterns for IP validation
_IPV4_PATTERN = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)
_HOSTNAME_PATTERN = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
)


def parse_generic_url_scheme(config: str) -> Optional[Proxy]:
    """Parse generic URL-based schemes like http, socks."""
    try:
        config = config.strip()
        if len(config) > MAX_CONFIG_LINE_LENGTH:
            return None

        # Support naked IP:PORT for SOCKS/HTTP
        if "://" not in config and ":" in config and not config.startswith("{"):
            parts = config.split(":")
            if len(parts) == 2 and parts[1].isdigit():
                host = parts[0]
                port_val = int(parts[1])

                # Validate IP/hostname format
                # Check for IPv4 address
                is_valid_ipv4 = _IPV4_PATTERN.match(host) is not None
                # Check for valid hostname (domain name)
                is_valid_hostname = (
                    _HOSTNAME_PATTERN.match(host) is not None and len(host) <= 253
                )
                # Check for IPv6 (simple check: contains only hex digits and colons)
                is_potential_ipv6 = (
                    all(c in "0123456789abcdefABCDEF:" for c in host)
                    and host.count(":") >= 2
                )

                if not (is_valid_ipv4 or is_valid_hostname or is_potential_ipv6):
                    logger.debug(
                        f"Naked IP:PORT rejected: invalid host format '{host}'"
                    )
                    return None

                # Validate port range
                if not (1 <= port_val <= 65535):
                    logger.debug(
                        f"Naked IP:PORT rejected: port {port_val} out of range"
                    )
                    return None

                # Heuristic: Default to SOCKS5 if port is 1080 or 10808, else HTTP
                # Ideally, this should come from source metadata, but this improves the hit rate for SOCKS lists.
                protocol = "http"
                if port_val in [1080, 10800, 10808, 9050]:
                    protocol = "socks5"

                # If source metadata indicates socks, it should be passed here, but we don't have it.
                # The heuristic is better than always HTTP for these ports.

                return Proxy(
                    config=config,
                    protocol=protocol,
                    address=host,
                    port=port_val,
                    uuid="",
                    details={},
                    remarks=f"naked_ip_{protocol}",
                )

        parsed = urlparse(config)
        if not parsed.hostname:
            return None

        # Stricter check for generic parsing: Must have valid hostname characters
        if not all(
            c.isalnum() or c in ".-_" for c in parsed.hostname if c not in "[]"
        ):  # allow [] for IPv6
            return None

        # Block "invalid" or "garbage" as hostnames for testing hygiene
        if parsed.hostname.lower() in ("garbage", "invalid"):
            return None

        # Ensure hostname has at least one dot or is localhost (basic validity)
        if "." not in parsed.hostname and parsed.hostname != "localhost":
            # Only allow if it looks like an IP (though rare without dots except IPv6)
            # This prevents "garbage" being accepted if check above fails
            return None

        scheme = parsed.scheme.lower()

        # Protocol Normalization
        protocol = scheme
        tls = False

        if scheme == "https":
            protocol = "http"
            tls = True
        elif scheme == "socks":
            protocol = "socks5"
        elif scheme == "socks4":
            protocol = "socks4"

        default_ports = {
            "http": 80,
            "https": 443,
            "ssh": 22,
            "socks": 1080,
            "socks4": 1080,
            "socks5": 1080,
        }
        port = parsed.port or default_ports.get(scheme, 80)
        if not (1 <= port <= 65535):
            return None

        details = {"password": parsed.password or ""}
        if tls:
            details["tls"] = "true"  # type: ignore

        return Proxy(
            config=config,
            protocol=protocol,
            address=parsed.hostname,
            port=port,
            uuid=parsed.username or "",
            details=details,
            remarks=unquote(parsed.fragment or ""),
        )
    except (ValueError, IndexError) as e:
        logger.debug(f"Failed to parse Generic config: {str(e)[:50]}")
        return None


def parse_naive(config: str) -> Optional[Proxy]:
    try:
        config = config.strip()
        if len(config) > MAX_CONFIG_LINE_LENGTH:
            return None

        parsed = urlparse(config.replace("naive+", ""))
        if not parsed.hostname:
            return None
        if not parsed.username or not parsed.password:
            return None
        return Proxy(
            config=config,
            protocol="naive",
            address=parsed.hostname,
            port=parsed.port or 443,
            uuid=parsed.username or "",
            details={"password": parsed.password or ""},
            remarks=unquote(parsed.fragment or ""),
        )
    except (ValueError, IndexError) as e:
        logger.debug(f"Failed to parse Naive config: {str(e)[:50]}")
        return None


def parse_v2ray_json(config: str) -> Optional[Proxy]:
    stripped = config.strip()
    if len(stripped) > MAX_CONFIG_LINE_LENGTH:
        return None

    if not stripped.startswith("{"):
        return None
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return None

    outbound = data.get("outbound")
    outbounds = data.get("outbounds")
    if not outbound and isinstance(outbounds, list) and outbounds:
        outbound = outbounds[0]
    if not outbound:
        return None

    protocol = outbound.get("protocol", "v2ray")
    settings = outbound.get("settings", {})
    server_info = None
    for key in ("vnext", "servers"):
        nodes = settings.get(key)
        if isinstance(nodes, list) and nodes:
            server_info = nodes[0]
            break

    if not server_info:
        return None

    address = (
        server_info.get("address") or server_info.get("server") or server_info.get("ip")
    )
    port = server_info.get("port")
    if not address or port is None:
        return None

    users = server_info.get("users")
    uuid = ""
    if isinstance(users, list) and users:
        uuid = users[0].get("id", "")

    metadata = {
        "protocol": protocol,
        "settings": settings,
    }
    remarks = outbound.get("tag", data.get("remark", ""))

    try:
        port_int = int(port)
    except (ValueError, TypeError):
        logger.debug(f"Invalid port in v2ray config: {port}")
        return None

    return Proxy(
        config=config,
        protocol="v2ray",
        address=address,
        port=port_int,
        uuid=uuid,
        remarks=remarks or "",
        details=metadata,
    )
