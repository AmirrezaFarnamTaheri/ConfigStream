"""
Serialization Helpers.
Converts Proxy objects to dictionary/JSON-safe formats.
"""

from typing import Dict, Any, List, Optional
from .models import Proxy

# Optional: Initialize tracker lazily if needed, but for serialization we might need to access the shared instance.
# Since serialize_proxy is usually called in loops, we should pass history data if available or fetch it efficiently.
# For simplicity in this function signature, we assume the pipeline injects history data or we use a global tracker.
# However, to avoid global state issues, let's assume the pipeline enriches the proxy object BEFORE serialization
# OR we modify this function to accept history.
#
# Strategy: The Proxy object doesn't hold full history (to save RAM). The HistoryTracker does.
# We will assume the Proxy object has a 'history' attribute injected dynamically during the output phase,
# or we just return what is on the object.
#
# Correction: The pipeline code (pipeline.py) creates the outputs. It should attach history there.
# Let's ensure the Proxy model supports 'history' attribute dynamically or just put it in details.

try:
    import orjson as json_lib
except ImportError:
    import json as json_lib  # type: ignore


def serialize_proxy(
    proxy: Proxy, history_points: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Convert Proxy object to dict.
    Args:
        proxy: The proxy object.
        history_points: Optional list of recent latency points for sparklines.
    """
    # Note: we include "country" for legacy/consistency with some parts,
    # but "country_code" is the ISO code.
    data = {
        "id": proxy.id,  # Useful for vector mapping
        "protocol": proxy.protocol,
        "address": proxy.address,
        "port": proxy.port,
        "country": proxy.country_code,
        "country_code": proxy.country_code,
        "city": proxy.city,
        "asn": proxy.asn,
        "org": proxy.org,
        "latency": proxy.latency,
        "is_working": proxy.is_working,
        "tags": proxy.tags,
        "last_checked": proxy.tested_at,
        "source": proxy.details.get("_source"),
        "security": proxy.security_issues,
        "details": proxy.details,
        "config": proxy.config,
        "remarks": proxy.remarks,
    }

    # Inject history if provided or attached
    if history_points:
        data["history"] = history_points
    elif hasattr(proxy, "history_points"):
        data["history"] = getattr(proxy, "history_points")

    return data


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
