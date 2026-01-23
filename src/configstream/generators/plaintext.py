# SPDX-License-Identifier: AGPL-3.0-or-later
import re
from typing import List, Optional

from ..adapters import ShadowrocketAdapter
from ..filtering import proxy_unique_key
from ..models import Proxy

_URI_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")


def _normalize_uri_key(uri: str) -> str:
    return uri.split("#", 1)[0].strip()


def _dedupe_key(proxy: Proxy, uri: str) -> object:
    scheme = uri.split("://", 1)[0].lower()
    if scheme == "vmess":
        return ("vmess", proxy_unique_key(proxy))
    return _normalize_uri_key(uri)


def _extract_uri(proxy: Proxy, adapter: ShadowrocketAdapter) -> Optional[str]:
    if proxy.protocol == "revived":
        return None

    raw = (proxy.config or "").strip()
    if raw and _URI_PATTERN.match(raw):
        if raw.lower().startswith("revived://"):
            return None
        return raw

    return adapter._reconstruct_uri(proxy) or None


def generate_plaintext_subscription(proxies: List[Proxy]) -> str:
    adapter = ShadowrocketAdapter()
    seen: set[object] = set()
    lines: List[str] = []

    for proxy in proxies:
        uri = _extract_uri(proxy, adapter)
        if not uri:
            continue
        dedupe_key = _dedupe_key(proxy, uri)
        if not dedupe_key or dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        lines.append(uri)

    return "\n".join(lines)
