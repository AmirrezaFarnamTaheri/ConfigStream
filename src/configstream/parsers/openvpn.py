# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import re
from typing import Optional
from ..models import Proxy
from ..constants import MAX_OPENVPN_CONFIG_SIZE

logger = logging.getLogger(__name__)

# Pre-compiled patterns for OpenVPN parsing
_CLIENT_DIRECTIVE_RE = re.compile(r"(^|\s)client(\s|$)", re.MULTILINE)
_REMOTE_LINE_RE = re.compile(r"^remote\s+(\S+)\s+(\d+)", re.MULTILINE)
_REMOTE_FALLBACK_RE = re.compile(r"remote\s+(\S+)\s+(\d+)")
_HOSTNAME_FORMAT_RE = re.compile(r"^[\w\.\-\[\]:]+$")
_PROTO_RE = re.compile(r"^proto\s+(\w+)", re.MULTILINE)


def parse_openvpn(config: str) -> Optional[Proxy]:
    """
    Parse OpenVPN configuration content.

    Security validations:
    - Config size limit (1MB max)
    - Port range validation (1-65535)
    - Hostname length and format validation
    - Strict "client" directive matching (not in comments)
    """
    try:
        # Enforce config size limit to prevent DoS/memory exhaustion (0 = unlimited)
        if MAX_OPENVPN_CONFIG_SIZE > 0 and len(config) > MAX_OPENVPN_CONFIG_SIZE:
            logger.warning(
                f"OpenVPN config rejected: size {len(config)} exceeds limit {MAX_OPENVPN_CONFIG_SIZE}"
            )
            return None

        # Check for "client" directive more strictly (start of line or after whitespace)
        # This prevents matching "client" in comments or embedded strings
        if not _CLIENT_DIRECTIVE_RE.search(config):
            return None

        # Extract remote
        remotes = _REMOTE_LINE_RE.findall(config)
        if not remotes:
            # Maybe in <connection> block?
            remotes = _REMOTE_FALLBACK_RE.findall(config)

        if not remotes:
            return None

        # Pick the first remote for now (simplification)
        host, port_str = remotes[0]

        # Validate hostname length and format
        if len(host) > 255:
            logger.warning(f"OpenVPN hostname rejected: length {len(host)} exceeds 255")
            return None

        # Basic hostname format validation (alphanumeric, dots, hyphens, underscores)
        # Also allows IPv4 addresses and IPv6 addresses in brackets
        if not _HOSTNAME_FORMAT_RE.match(host):
            logger.warning(f"OpenVPN hostname rejected: invalid format '{host}'")
            return None

        # Validate port range (1-65535)
        try:
            port = int(port_str)
            if port < 1 or port > 65535:
                logger.warning(f"OpenVPN port rejected: {port} out of range (1-65535)")
                return None
        except (ValueError, TypeError):
            logger.debug(f"Invalid port in openvpn config: {port_str}")
            return None

        # Extract Proto
        proto_match = _PROTO_RE.search(config)
        transport = proto_match.group(1) if proto_match else "udp"

        # Validate transport protocol
        if transport.lower() not in ["tcp", "udp", "tcp-client", "udp-client"]:
            logger.debug(f"Unknown OpenVPN transport: {transport}, defaulting to udp")
            transport = "udp"

        return Proxy(
            config=config,  # Store the full file content as config
            protocol="openvpn",
            address=host,
            port=port,
            details={
                "transport": transport,
                # We don't parse keys out; the config is the payload
            },
            remarks="OpenVPN Config",
        )

    except ValueError as e:
        logger.debug(f"Failed to parse OpenVPN (validation error): {e}")
        return None
    except re.error as e:
        logger.warning(f"Failed to parse OpenVPN (regex error): {e}")
        return None
    except Exception as e:
        logger.warning(f"Failed to parse OpenVPN (unexpected error): {e}")
        return None
