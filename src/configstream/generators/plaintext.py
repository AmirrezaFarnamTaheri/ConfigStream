# SPDX-License-Identifier: AGPL-3.0-or-later
import re
import urllib.parse
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
    # Revived proxies: reconstruct URI from origin_proxy stored in details
    if proxy.protocol == "revived" or (proxy.config or "").lower().startswith(
        "revived://"
    ):
        origin = (proxy.details or {}).get("origin_proxy")
        if not origin or not isinstance(origin, dict):
            return None
        try:
            origin_proxy = Proxy(**origin)
            tag = (
                "Revived"
                if not (proxy.details or {}).get("use_vwarp")
                else "Revived-VWARP"
            )
            origin_proxy.remarks = (
                f"[{tag}] {origin_proxy.remarks or origin_proxy.protocol}"
            )
            return _extract_uri(origin_proxy, adapter)
        except Exception:
            return None

    raw = (proxy.config or "").strip()
    if raw and _URI_PATTERN.match(raw):
        scheme = raw.split("://", 1)[0].lower()
        if scheme == "vmess" or scheme == "socks":
            rebuilt = adapter._reconstruct_uri(proxy)
            if rebuilt:
                return rebuilt
        if proxy.remarks:
            safe_name = urllib.parse.quote(proxy.remarks)
            base = raw.split("#", 1)[0]
            return f"{base}#{safe_name}"
        return raw

    return adapter._reconstruct_uri(proxy) or None


def _sanitize_uri(uri: str) -> Optional[str]:
    """Reject URIs containing null bytes or non-printable binary data."""
    if "\x00" in uri:
        return None
    # URL-encode any remaining raw bytes that slipped through parsers
    # (e.g. TLS prefix obfuscation fields with raw binary)
    try:
        uri.encode("utf-8")
    except UnicodeEncodeError:
        return None
    return uri


def generate_plaintext_subscription(proxies: List[Proxy]) -> str:
    adapter = ShadowrocketAdapter()
    seen: set[object] = set()
    lines: List[str] = []
    protocol_order = [
        "shadowsocks",
        "ss2022",
        "vless",
        "vmess",
        "trojan",
        "hysteria2",
        "hysteria",
        "tuic",
        "wireguard",
        "naive",
        "ssh",
        "http",
        "socks5",
        "socks4",
        "socks",
    ]

    grouped: dict[str, List[Proxy]] = {}
    for proxy in proxies:
        proto_key = proxy.protocol or "unknown"
        if proto_key == "socks":
            proto_key = "socks5"
        elif proto_key == "ss":
            proto_key = "shadowsocks"
        elif proto_key == "hy2":
            proto_key = "hysteria2"
        elif proto_key == "wg":
            proto_key = "wireguard"
        grouped.setdefault(proto_key, []).append(proxy)

    ordered_protocols = protocol_order + sorted(
        [p for p in grouped.keys() if p not in protocol_order]
    )

    for proto in ordered_protocols:
        for proxy in grouped.get(proto, []):
            uri = _extract_uri(proxy, adapter)
            if not uri:
                continue
            uri = _sanitize_uri(uri)
            if not uri:
                continue
            dedupe_key = _dedupe_key(proxy, uri)
            if not dedupe_key or dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            lines.append(uri)

    return "\n".join(lines)
