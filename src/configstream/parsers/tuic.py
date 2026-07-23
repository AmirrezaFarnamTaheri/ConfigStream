# SPDX-License-Identifier: AGPL-3.0-or-later
"""TUIC v5 protocol URI parser."""

import urllib.parse
from typing import Optional
from ..models import Proxy

def parse_tuic(line: str) -> Optional[Proxy]:
    """Parse a tuic:// URI into a Proxy model."""
    raw = (line or "").strip()
    if not raw.lower().startswith("tuic://"):
        return None
    try:
        parsed = urllib.parse.urlparse(raw)
        host = parsed.hostname
        port = parsed.port or 8443
        if not host:
            return None

        uuid_val = parsed.username or ""
        password_val = parsed.password or ""
        
        # Mandatory field validation: TUIC requires UUID
        if not uuid_val:
            return None

        remarks = urllib.parse.unquote(parsed.fragment) if parsed.fragment else ""

        params = urllib.parse.parse_qs(parsed.query)
        details = {
            "password": password_val or uuid_val,
            "congestion_control": params.get("congestion_control", ["bbr"])[0],
            "alpn": params.get("alpn", ["h3"])[0],
        }

        return Proxy(
            config=raw,
            protocol="tuic",
            address=host,
            port=port,
            uuid=uuid_val,
            remarks=remarks,
            details=details,
        )
    except Exception:
        return None
