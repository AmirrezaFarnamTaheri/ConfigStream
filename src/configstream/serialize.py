"""
Serialization Helpers.
Converts Proxy objects to dictionary/JSON-safe formats.
"""

from typing import Dict, Any
from .models import Proxy

try:
    import orjson as json_lib
except ImportError:
    import json as json_lib  # type: ignore


def serialize_proxy(proxy: Proxy) -> Dict[str, Any]:
    """
    Convert Proxy object to dict.
    """
    # Note: we include "country" for legacy/consistency with some parts,
    # but "country_code" is the ISO code.
    return {
        "protocol": proxy.protocol,
        "address": proxy.address,
        "port": proxy.port,
        "country": proxy.country_code,  # Mapped to country code in output, but kept as "country" key for frontend compat
        "country_code": proxy.country_code,  # Explicit field
        "city": proxy.city,
        "asn": proxy.asn,
        "org": proxy.org,
        "latency": proxy.latency,
        "is_working": proxy.is_working,
        "last_checked": proxy.tested_at,
        "source": proxy.details.get("_source"),
        "security": proxy.security_issues,
        "details": proxy.details,
        "config": proxy.config,
        "remarks": proxy.remarks,
        # Exclude huge raw config to save space in summary if not needed,
        # but frontend uses `p.config` for copy button.
    }


def to_json(data: Any) -> str:
    """
    Dump to JSON string.
    """
    if hasattr(json_lib, "dumps"):
        # Standard json or compatible
        val = json_lib.dumps(data)
        if isinstance(val, bytes):
            return val.decode("utf-8")
        return str(val)  # Ensure string return
    else:
        # Fallback
        import json

        return json.dumps(data, indent=2, default=str)
