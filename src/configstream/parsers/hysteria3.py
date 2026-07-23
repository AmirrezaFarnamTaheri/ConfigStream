# SPDX-License-Identifier: AGPL-3.0-or-later
"""Hysteria3 protocol URI parser."""

import urllib.parse
from typing import Optional
from ..models import Proxy

def parse_hysteria3(line: str) -> Optional[Proxy]:
    """Parse a hy3:// or hysteria3:// URI into a Proxy model."""
    raw = (line or "").strip()
    lower = raw.lower()
    if not (lower.startswith("hy3://") or lower.startswith("hysteria3://")):
        return None
    try:
        scheme = "hy3://" if lower.startswith("hy3://") else "hysteria3://"
        body = raw[len(scheme):]
        parsed = urllib.parse.urlparse("http://" + body if not body.startswith("http://") else body)

        host = parsed.hostname
        port = parsed.port or 443
        if not host:
            return None

        auth_val = parsed.username or ""
        if not auth_val:
            return None

        remarks = urllib.parse.unquote(parsed.fragment) if parsed.fragment else ""

        params = urllib.parse.parse_qs(parsed.query)
        details = {
            "auth": auth_val,
            "obfs": params.get("obfs", [""])[0],
            "obfs_password": params.get("obfs-password", [""])[0],
            "sni": params.get("sni", [""])[0],
        }

        return Proxy(
            config=raw,
            protocol="hysteria3",
            address=host,
            port=port,
            uuid="",
            remarks=remarks,
            details=details,
        )
    except Exception:
        return None
