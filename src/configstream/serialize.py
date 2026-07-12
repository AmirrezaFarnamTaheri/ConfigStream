# SPDX-License-Identifier: AGPL-3.0-or-later
"""Serialization helpers for the public proxy contract.

Runtime proxy objects carry private provenance and diagnostics. Public output is
therefore constructed through an explicit, recursively sanitized boundary.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Union

from .converters.chains import chain_outbounds_from_details
from .models import Proxy

try:
    import orjson as json_lib
except ImportError:
    import json as json_lib  # type: ignore


_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)

# These fields are internal provenance, transport credentials, acquisition
# material, or raw payloads. They may exist in runtime objects but never cross
# the public serialization boundary, at any nesting depth.
_PRIVATE_DETAIL_KEYS = {
    "source",
    "source_url",
    "source_uri",
    "origin_url",
    "subscription_url",
    "request_headers",
    "response_headers",
    "authorization",
    "api_key",
    "apikey",
    "token",
    "access_token",
    "refresh_token",
    "password",
    "private_key",
    "pre_shared_key",
    "psk",
    "raw",
    "raw_payload",
    "raw_config",
    "original_config",
}


def _public_uuid_value(proxy: Proxy) -> str:
    raw = (proxy.uuid or "").strip()
    return raw if raw and _UUID_RE.fullmatch(raw) else ""


def _public_source_id(raw_source: object) -> Optional[str]:
    """Return a stable, non-reversible provider correlation identifier."""

    if not isinstance(raw_source, str) or not raw_source.strip():
        return None
    return hashlib.sha256(raw_source.strip().encode("utf-8")).hexdigest()[:16]


def _sanitize_public_value(value: Any) -> Any:
    if isinstance(value, Proxy):
        # Nested Proxy values are converted through their JSON model first and
        # then sanitized recursively; this avoids leaking arbitrary attributes.
        return _sanitize_public_value(value.model_dump(mode="json"))
    if isinstance(value, dict):
        cleaned: Dict[str, Any] = {}
        for key, item in value.items():
            name = str(key)
            lowered = name.lower()
            if name.startswith("_") or lowered.startswith("has_"):
                continue
            if lowered in _PRIVATE_DETAIL_KEYS:
                continue
            cleaned[name] = _sanitize_public_value(item)
        return cleaned
    if isinstance(value, (list, tuple)):
        return [_sanitize_public_value(item) for item in value]
    if isinstance(value, set):
        return sorted(_sanitize_public_value(item) for item in value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def serialize_proxy(
    proxy: Proxy, history_points: Optional[List[float]] = None
) -> Dict[str, Any]:
    """Convert a runtime proxy to the explicit public dictionary contract."""

    config_value = proxy.config
    runtime_details = proxy.details or {}
    details_value = _sanitize_public_value(runtime_details)
    if not isinstance(details_value, dict):
        details_value = {}

    if proxy.protocol == "revived" or (proxy.config or "").startswith("revived://"):
        chain_outbounds = chain_outbounds_from_details(runtime_details)
        if chain_outbounds:
            config_value = _build_chain_config(chain_outbounds)

        # Preserve only non-secret reconstruction metadata. The full nested
        # origin proxy/config must remain private.
        origin = runtime_details.get("origin_proxy")
        if isinstance(origin, dict):
            details_value["origin"] = {
                "protocol": str(origin.get("protocol") or ""),
                "address": str(origin.get("address") or ""),
                "port": int(origin.get("port") or 0),
                "resolved_ip": str(origin.get("resolved_ip") or ""),
                "remarks": str(origin.get("remarks") or ""),
            }

    raw_source = runtime_details.get("_source")
    data: Dict[str, Any] = {
        "id": proxy.id,
        "protocol": proxy.protocol,
        "address": proxy.address,
        "port": proxy.port,
        "uuid": _public_uuid_value(proxy),
        "city": proxy.city,
        "asn": proxy.asn,
        "org": proxy.org,
        "latency": proxy.latency,
        "is_working": proxy.is_working,
        "tags": list(proxy.tags),
        "last_checked": proxy.tested_at,
        "source": _public_source_id(raw_source),
        "security": _sanitize_public_value(proxy.security_issues),
        "details": details_value,
        "config": config_value,
        "remarks": proxy.remarks,
        "process": proxy.process,
    }

    history = history_points or getattr(proxy, "history", None)
    if history:
        data["history"] = list(history)
    return data


def _build_chain_config(chain_outbounds: List[Dict[str, Any]]) -> str:
    """Build a minimal sing-box JSON config from safe chain outbounds."""

    clean: List[Dict[str, Any]] = []
    for outbound in chain_outbounds:
        if not isinstance(outbound, dict):
            continue
        cleaned = {
            key: value
            for key, value in outbound.items()
            if not str(key).startswith("_")
        }
        cleaned.pop("region", None)
        cleaned.pop("origin_proxy", None)
        clean.append(cleaned)
    if not clean:
        return ""
    return json.dumps({"outbounds": clean}, ensure_ascii=False)


def _json_default(obj: Any) -> Any:
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, tuple):
        return list(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


def to_json(data: Any) -> str:
    """Dump a JSON-safe string with an orjson fast path."""

    try:
        result: Union[str, bytes] = json_lib.dumps(data)
    except TypeError:
        result = json.dumps(data, indent=2, default=_json_default)
    return result.decode("utf-8") if isinstance(result, bytes) else str(result)
