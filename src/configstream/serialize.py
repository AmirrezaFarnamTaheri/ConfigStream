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
    return {
        "protocol": proxy.protocol,
        "address": proxy.address,
        "port": proxy.port,
        "country": proxy.country_code,
        "latency": proxy.latency,
        "is_working": proxy.is_working,
        "last_checked": proxy.tested_at,
        "source": proxy.details.get("_source"),
        "security": proxy.security_issues,
        # Exclude huge raw config to save space in summary, include only if needed
        # "config": proxy.config
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
        return val
    else:
        # Fallback
        import json
        return json.dumps(data, indent=2, default=str)
