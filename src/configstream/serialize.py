# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Serialization Helpers.
Converts Proxy objects to dictionary/JSON-safe formats.
"""

from typing import Dict, Any, List, Optional, Union
from .models import Proxy

# Proxy object serialization.
# Note: History data (latency points) is injected dynamically by the pipeline before serialization,
# or passed explicitly to serialize_proxy to avoid carrying heavy history in the Proxy model constantly.

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
        "uuid": proxy.uuid,  # Critical for VLESS/Trojan/VMess reconstruction
        "country": proxy.country_code,
        "country_code": proxy.country_code,
        "city": proxy.city,
        "asn": proxy.asn,
        "org": proxy.org,
        "latency": proxy.latency,
        "is_working": proxy.is_working,
        "tags": proxy.tags,
        "last_checked": proxy.tested_at,
        # [FIX] Guard against None details
        "source": (proxy.details or {}).get("_source"),
        "security": proxy.security_issues,
        "details": proxy.details,
        "config": proxy.config,
        "remarks": proxy.remarks,
        "process": proxy.process,
    }

    # Inject history if provided or attached
    if history_points:
        data["history"] = history_points
    elif getattr(proxy, "history", None):
        data["history"] = proxy.history
    elif hasattr(proxy, "history_points"):
        data["history"] = getattr(proxy, "history_points")

    return data


def _json_default(obj: Any) -> Any:
    """Custom JSON serializer for types not handled by default.

    [FIX] Handles set, tuple, datetime, and other common Python types
    to prevent TypeError crashes during output generation (Zone 6).
    """
    if isinstance(obj, set):
        return sorted(obj)  # Consistent ordering for sets
    if isinstance(obj, tuple):
        return list(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    # datetime handling
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


def to_json(data: Any) -> str:
    """
    Dump to JSON string.
    """
    if hasattr(json_lib, "dumps"):
        # Standard json or compatible
        try:
            result: Union[str, bytes] = json_lib.dumps(data)
        except TypeError:
            # [FIX] Fallback with custom default handler for non-serializable types
            import json
            result = json.dumps(data, indent=2, default=_json_default)
        if isinstance(result, bytes):
            return result.decode("utf-8")
        return str(result)  # Ensure string return
    else:
        # Fallback
        import json
        return json.dumps(data, indent=2, default=_json_default)
