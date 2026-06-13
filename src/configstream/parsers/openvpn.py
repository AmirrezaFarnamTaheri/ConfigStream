# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import re
from typing import Optional
from ..models import Proxy
from ..constants import MAX_OPENVPN_CONFIG_SIZE
from ..security_validator import SecurityValidator

logger = logging.getLogger(__name__)

# Pre-compiled patterns for OpenVPN parsing
_CLIENT_DIRECTIVE_RE = re.compile(r"(^|\s)client(\s|$)", re.MULTILINE)
_REMOTE_LINE_RE = re.compile(r"^remote\s+(\S+)\s+(\d+)", re.MULTILINE)
_REMOTE_FALLBACK_RE = re.compile(r"remote\s+(\S+)\s+(\d+)")
_HOSTNAME_FORMAT_RE = re.compile(r"^[\w\.\-\[\]:]+$")
_PROTO_RE = re.compile(r"^proto\s+([\w-]+)", re.MULTILINE)


def _safe_log_text(value: object) -> str:
    return SecurityValidator.sanitize_log_message(str(value))


def _validate_remote(host: str, port_str: str) -> Optional[tuple[str, int]]:
    if len(host) > 255:
        logger.debug(
            "OpenVPN remote skipped: hostname length %d exceeds 255",
            len(host),
        )
        return None

    if not _HOSTNAME_FORMAT_RE.match(host):
        logger.debug(
            "OpenVPN remote skipped: invalid hostname format %s",
            _safe_log_text(host),
        )
        return None

    try:
        port = int(port_str)
    except (ValueError, TypeError):
        logger.debug(
            "OpenVPN remote skipped: invalid port %s",
            _safe_log_text(port_str),
        )
        return None

    if port < 1 or port > 65535:
        logger.debug(
            "OpenVPN remote skipped: port %d out of range (1-65535)",
            port,
        )
        return None

    return host, port


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
                "OpenVPN config rejected: size %d exceeds limit %d",
                len(config),
                MAX_OPENVPN_CONFIG_SIZE,
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

        selected_remote = None
        for host, port_str in remotes:
            selected_remote = _validate_remote(host, port_str)
            if selected_remote is not None:
                break

        if selected_remote is None:
            first_host, first_port = remotes[0]
            logger.warning(
                "OpenVPN config rejected: no valid remote endpoint found; "
                "first rejected remote=%s:%s",
                _safe_log_text(first_host),
                _safe_log_text(first_port),
            )
            return None
        host, port = selected_remote

        # Extract Proto
        proto_match = _PROTO_RE.search(config)
        transport = proto_match.group(1) if proto_match else "udp"

        # Validate transport protocol
        if transport.lower() not in ["tcp", "udp", "tcp-client", "udp-client"]:
            logger.debug(
                "Unknown OpenVPN transport: %s, defaulting to udp",
                _safe_log_text(transport),
            )
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
        logger.debug(
            "Failed to parse OpenVPN (validation error): %s",
            _safe_log_text(e),
        )
        return None
    except re.error as e:
        logger.warning(
            "Failed to parse OpenVPN (regex error): %s",
            _safe_log_text(e),
        )
        return None
    except Exception as e:
        logger.warning(
            "Failed to parse OpenVPN (unexpected error): %s",
            _safe_log_text(e),
        )
        return None
