# SPDX-License-Identifier: AGPL-3.0-or-later
"""Hysteria3 protocol URI parser."""

import logging
import urllib.parse
from typing import Optional

from ..models import Proxy
from ..security_validator import SecurityValidator

logger = logging.getLogger(__name__)

# Obfuscation modes that require a password.
_OBFS_REQUIRING_PASSWORD = frozenset({"salamander", "xplus"})


def parse_hysteria3(line: str) -> Optional[Proxy]:
    """Parse a hy3:// or hysteria3:// URI into a Proxy model.

    Supports: auth (username), obfs mode/password, SNI, multi-port hint.
    Drops configurations missing required fields.
    """
    raw = (line or "").strip()
    lower = raw.lower()
    if not (lower.startswith("hy3://") or lower.startswith("hysteria3://")):
        return None
    try:
        # Normalize scheme for urlparse
        if lower.startswith("hy3://"):
            normalized = "http://" + raw[len("hy3://") :]
        else:
            normalized = "http://" + raw[len("hysteria3://") :]

        parsed = urllib.parse.urlparse(normalized)
        host = parsed.hostname
        if not host:
            logger.debug("Hysteria3 parser: missing host")
            return None

        try:
            port = int(parsed.port) if parsed.port is not None else 443
            if not (1 <= port <= 65535):
                raise ValueError(f"port {port} out of range")
        except (ValueError, TypeError) as exc:
            logger.debug(
                "Hysteria3 parser: invalid port – %s",
                SecurityValidator.sanitize_log_message(str(exc)),
            )
            return None

        auth_val = urllib.parse.unquote(parsed.username or "")
        if not auth_val:
            logger.debug("Hysteria3 parser: missing auth/username; dropping proxy")
            return None

        remarks = urllib.parse.unquote(parsed.fragment) if parsed.fragment else ""
        params = urllib.parse.parse_qs(parsed.query)

        obfs_mode = params.get("obfs", [""])[0]
        obfs_password = params.get("obfs-password", [""])[0]

        # Reject if obfuscation mode requires a password but none provided.
        if obfs_mode in _OBFS_REQUIRING_PASSWORD and not obfs_password:
            logger.debug(
                "Hysteria3 parser: obfs mode '%s' requires password; dropping",
                SecurityValidator.sanitize_log_message(obfs_mode),
            )
            return None

        details = {
            "auth": auth_val,
            "obfs": obfs_mode,
            "obfs_password": obfs_password,
            "sni": params.get("sni", [""])[0],
        }

        # Extended spec fields
        if "multi-port" in params:
            details["multi_port"] = params["multi-port"][0]
        if "obfs-v2" in params:
            details["obfs_v2"] = params["obfs-v2"][0]
        if "padding" in params:
            details["padding_len"] = params["padding"][0]

        return Proxy(
            config=raw,
            protocol="hysteria3",
            address=host,
            port=port,
            uuid="",  # Hysteria3 uses passphrase auth, not UUID
            remarks=remarks,
            details=details,
        )
    except (ValueError, AttributeError, UnicodeDecodeError) as exc:
        logger.debug(
            "Hysteria3 parser: dropping malformed URI – %s",
            SecurityValidator.sanitize_log_message(str(exc)),
        )
        return None
