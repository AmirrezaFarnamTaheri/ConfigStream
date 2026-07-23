# SPDX-License-Identifier: AGPL-3.0-or-later
"""TUIC v5 protocol URI parser."""

import logging
import urllib.parse
from typing import List, Optional

from ..models import Proxy
from ..security_validator import SecurityValidator

logger = logging.getLogger(__name__)


def parse_tuic(line: str) -> Optional[Proxy]:
    """Parse a tuic:// URI into a Proxy model.

    TUIC v5 requires both UUID (username) and password fields.
    Falls back to empty password with a debug log rather than using UUID as password.
    """
    raw = (line or "").strip()
    if not raw.lower().startswith("tuic://"):
        return None
    try:
        parsed = urllib.parse.urlparse(raw)
        host = parsed.hostname
        if not host:
            logger.debug(
                "TUIC parser: missing host in %s",
                SecurityValidator.sanitize_log_message(raw[:60]),
            )
            return None

        try:
            port = int(parsed.port) if parsed.port is not None else 443
            if not (1 <= port <= 65535):
                raise ValueError(f"port {port} out of range")
        except (ValueError, TypeError) as exc:
            logger.debug(
                "TUIC parser: invalid port – %s",
                SecurityValidator.sanitize_log_message(str(exc)),
            )
            return None

        uuid_val = parsed.username or ""
        password_val = parsed.password or ""

        # Mandatory field: TUIC requires UUID for authentication token derivation.
        if not uuid_val:
            logger.debug("TUIC parser: missing UUID (username) field")
            return None

        # Password is mandatory in TUIC v5 – UUID cannot substitute for it.
        if not password_val:
            logger.debug("TUIC parser: missing password; dropping proxy")
            return None

        remarks = urllib.parse.unquote(parsed.fragment) if parsed.fragment else ""

        params = urllib.parse.parse_qs(parsed.query)

        cc_algo = params.get("congestion_control", params.get("cc_algo", ["bbr"]))[0]
        alpn_raw = params.get("alpn", ["h3"])[0]
        alpn_list: List[str] = [a.strip() for a in alpn_raw.split(",") if a.strip()]
        if not alpn_list:
            alpn_list = ["h3"]

        details = {
            "password": password_val,
            "congestion_control": cc_algo,
            "cc_algo": cc_algo,  # canonical alias per spec
            "alpn": alpn_list,
        }
        # Preserve extra query parameters
        for key in ("max_idle_time", "initial_max_streams", "disable_sni", "reduce_rtt"):
            if key in params:
                try:
                    details[key] = int(params[key][0])
                except (ValueError, IndexError):
                    details[key] = params[key][0]

        return Proxy(
            config=raw,
            protocol="tuic",
            address=host,
            port=port,
            uuid=uuid_val,
            remarks=remarks,
            details=details,
        )
    except (ValueError, AttributeError, UnicodeDecodeError) as exc:
        logger.debug(
            "TUIC parser: dropping malformed URI – %s",
            SecurityValidator.sanitize_log_message(str(exc)),
        )
        return None
