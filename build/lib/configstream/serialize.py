# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Serialization Helpers.
Converts Proxy objects to dictionary/JSON-safe formats.
"""

import json
import re
import hashlib
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional, Union

from .models import Proxy
from .converters.chains import chain_outbounds_from_details

# Proxy object serialization.
# Note: History data (latency points) is injected dynamically by the pipeline before serialization,
# or passed explicitly to serialize_proxy to avoid carrying heavy history in the Proxy model constantly.

try:
    import orjson as json_lib
except ImportError:
    import json as json_lib  # type: ignore


_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)


def _public_uuid_value(proxy: Proxy) -> str:
    raw = (proxy.uuid or "").strip()
    if not raw:
        return ""
    if _UUID_RE.match(raw):
        return raw
    return ""


def _sanitize_source(raw_source: Optional[str]) -> Optional[str]:
    """Sanitize the source URL to prevent leaking subscription tokens."""
    if not raw_source:
        return None
    try:
        parsed = urlparse(raw_source)
        if parsed.netloc:
            # Return just the domain/host
            return parsed.netloc
    except Exception:
        # Fall through to deterministic hash fallback
        return hashlib.sha256(raw_source.encode("utf-8")).hexdigest()[:12]
    # Fallback to a short hash if it's not a parsable URL
    return hashlib.sha256(raw_source.encode("utf-8")).hexdigest()[:12]


def serialize_proxy(
    proxy: Proxy, history_points: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Convert Proxy object to dict.
    Args:
        proxy: The proxy object.
        history_points: Optional list of recent latency points for sparklines.
    """
    # For revived/chain proxies, generate a mini sing-box JSON config
    # that v2rayN / xray / nekoray / Hiddify can import directly.
    config_value = proxy.config
    details_value = proxy.details
    if isinstance(details_value, dict):
        details_value = {
            k: v for k, v in details_value.items() if not k.startswith("has_")
        }
        if isinstance(details_value.get("chain"), list):
            serialized_chain: List[Dict[str, Any]] = []
            for hop in details_value.get("chain", []):
                if isinstance(hop, Proxy):
                    serialized_chain.append(hop.model_dump(mode="json"))
                elif isinstance(hop, dict):
                    serialized_chain.append(hop)
            details_value = dict(details_value)
            details_value["chain"] = serialized_chain

    if proxy.protocol == "revived" or (proxy.config or "").startswith("revived://"):
        chain_obs = chain_outbounds_from_details(proxy.details or {})
        if chain_obs:
            config_value = _build_chain_config(chain_obs)
        # Strip heavy origin_proxy blob from serialized details but
        # preserve a compact origin_config for URI reconstruction in
        # plaintext/base64 generators after merge deserialization.
        if isinstance(details_value, dict) and "origin_proxy" in details_value:
            origin_blob = details_value["origin_proxy"]
            details_value = {
                k: v for k, v in details_value.items() if k != "origin_proxy"
            }
            if isinstance(origin_blob, dict) and "origin_config" not in details_value:
                details_value["origin_config"] = {
                    "config": origin_blob.get("config", ""),
                    "protocol": origin_blob.get("protocol", ""),
                    "address": origin_blob.get("address", ""),
                    "port": origin_blob.get("port", 0),
                    "uuid": origin_blob.get("uuid", ""),
                    "resolved_ip": origin_blob.get("resolved_ip", ""),
                    "remarks": origin_blob.get("remarks", ""),
                    "details": origin_blob.get("details") or {},
                }

    raw_source = (proxy.details or {}).get("_source")

    data = {
        "id": proxy.id,  # Useful for vector mapping
        "protocol": proxy.protocol,
        "address": proxy.address,
        "port": proxy.port,
        "uuid": _public_uuid_value(proxy),
        "city": proxy.city,
        "asn": proxy.asn,
        "org": proxy.org,
        "latency": proxy.latency,
        "is_working": proxy.is_working,
        "tags": proxy.tags,
        "last_checked": proxy.tested_at,
        # Guard against None details and sanitize source
        "source": _sanitize_source(raw_source),
        "security": proxy.security_issues,
        "details": details_value,
        "config": config_value,
        "remarks": proxy.remarks,
        "process": proxy.process,
    }

    # Inject history if provided or attached
    if history_points:
        data["history"] = history_points
    else:
        hist = getattr(proxy, "history", None) or getattr(proxy, "history_points", None)
        if hist:
            data["history"] = hist

    return data


def _build_chain_config(chain_outbounds: List[Dict[str, Any]]) -> str:
    """
    Build a mini sing-box JSON config from chain outbounds.
    Importable by v2rayN / xray / nekoray / Hiddify.
    """
    clean = []
    for ob in chain_outbounds:
        if not isinstance(ob, dict):
            continue
        # Strip internal metadata that sing-box rejects
        cleaned = {k: v for k, v in ob.items() if not k.startswith("_")}
        cleaned.pop("region", None)
        cleaned.pop("origin_proxy", None)
        clean.append(cleaned)
    if not clean:
        return ""
    return json.dumps({"outbounds": clean}, ensure_ascii=False)


def _json_default(obj: Any) -> Any:
    """Custom JSON serializer for types not handled by default.

    Handles set, tuple, datetime, and other common Python types
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
    Dump to JSON string.  Uses orjson if available, falling back to stdlib json.
    """
    try:
        result: Union[str, bytes] = json_lib.dumps(data)
    except TypeError:
        # Fallback with custom default handler for non-serializable types
        import json

        result = json.dumps(data, indent=2, default=_json_default)
    if isinstance(result, bytes):
        return result.decode("utf-8")
    return str(result)
