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
    Includes all fields required by the frontend for health calculation and display.
    """
    return {
        "id": proxy.id,
        "protocol": proxy.protocol,
        "address": proxy.address,
        "port": proxy.port,
        "country_code": proxy.country_code,
        "city": proxy.city,
        "asn": proxy.asn,
        "org": proxy.org,
        "latency": proxy.latency,
        "is_working": proxy.is_working,
        "tested_at": proxy.tested_at,
        "remarks": proxy.remarks,
        "details": proxy.details,
        "security_issues": proxy.security_issues,
        "config": proxy.config,  # Frontend copy functionality needs this
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
