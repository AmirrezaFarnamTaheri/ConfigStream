# SPDX-License-Identifier: AGPL-3.0-or-later
# src/configstream/tagging.py
"""
This module handles the in-place renaming (tagging) of proxy objects
based on a user-defined template.
"""

import logging
import re
from typing import List, Optional, Dict
from .models import Proxy
from .utils.bool_parser import parse_tls_flag

logger = logging.getLogger(__name__)


def get_flag_emoji(country_code: str) -> str:
    """
    Convert a 2-letter ISO country code to its flag emoji.
    Uses regional indicator symbols which combine to form flag emojis.
    """
    if not country_code or len(country_code) != 2:
        return "🌐"  # Globe for unknown
    try:
        # Convert each letter to regional indicator symbol
        # A = U+1F1E6, B = U+1F1E7, etc.
        return "".join(chr(ord(c.upper()) + 127397) for c in country_code)
    except (ValueError, TypeError):
        return "🌐"


class FmtWrapper(dict):
    """
    A dictionary wrapper that returns an empty string "" for missing keys
    or keys whose value is None. This prevents errors during string formatting.
    """

    def __missing__(self, key: str) -> str:
        return ""


def _normalize_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.\-+]", "", value).strip()


def _transport_label(details: Dict[str, object], protocol: str) -> str:
    raw = details.get("net") or details.get("type") or details.get("transport")
    if not raw:
        if protocol in ("hysteria", "hysteria2", "tuic"):
            return "QUIC"
        return "TCP"
    raw_val = str(raw).lower().strip()
    mapping = {
        "ws": "WS",
        "websocket": "WS",
        "grpc": "GRPC",
        "h2": "H2",
        "http": "H2",
        "tcp": "TCP",
        "kcp": "KCP",
        "quic": "QUIC",
        "udp": "UDP",
    }
    return mapping.get(raw_val, raw_val.upper())


def _security_label(details: Dict[str, object]) -> str:
    security = str(details.get("security", "")).lower().strip()
    if security == "reality":
        return "REALITY"
    if security in ("tls", "xtls"):
        return "TLS"
    if parse_tls_flag(details.get("tls")):
        return "TLS"
    return ""


def build_proxy_stack(proxy: Proxy) -> str:
    details = proxy.details or {}
    proto = (proxy.protocol or "").upper().strip()
    if proto == "REVIVED":
        origin = details.get("origin_proxy")
        if isinstance(origin, dict):
            origin_proto = origin.get("protocol")
            if isinstance(origin_proto, str) and origin_proto.strip():
                proto = f"REVIVED-{origin_proto.upper().strip()}"
    parts: List[str] = [proto] if proto else []

    transport = _transport_label(details, (proxy.protocol or "").lower())
    if transport:
        parts.append(transport)

    security = _security_label(details)
    if security:
        parts.append(security)

    if details.get("is_revived"):
        parts.append("VWARP" if details.get("use_vwarp") else "WARP")

    if proxy.protocol in ("shadowsocks", "ss2022"):
        method = details.get("method")
        if isinstance(method, str) and method.strip():
            parts.append(method.strip().upper())

    return "+".join(p for p in parts if p)


def build_proxy_tags(proxy: Proxy) -> List[str]:
    tags: List[str] = []
    details = proxy.details or {}
    proto = (proxy.protocol or "").upper().strip()
    if proto:
        tags.append(f"PROTO:{proto}")

    transport = _transport_label(details, (proxy.protocol or "").lower())
    if transport:
        tags.append(f"TRANS:{transport}")

    security = _security_label(details)
    if security:
        tags.append(f"SEC:{security}")

    process = (proxy.process or "native").upper()
    tags.append(f"PROC:{process}")

    if details.get("is_revived"):
        tags.append("REVIVED")
        tags.append("VWARP" if details.get("use_vwarp") else "WARP")

    if proxy.is_working:
        tags.append("STATUS:UP")
    else:
        tags.append("STATUS:DOWN")

    cc = (proxy.country_code or "").upper()
    tags.append(f"GEO:{get_flag_emoji(cc)}")

    if proxy.latency is not None:
        tags.append(f"LAT:{int(proxy.latency)}MS")

    if proxy.security_issues and isinstance(proxy.security_issues, dict):
        for category, entries in proxy.security_issues.items():
            if not entries:
                continue
            cat_token = _normalize_token(str(category)).upper()
            for reason in entries:
                reason_token = _normalize_token(str(reason))
                if cat_token and cat_token not in ("POLICY",):
                    if reason_token:
                        tags.append(f"ISSUE:{cat_token}:{reason_token}")
                    else:
                        tags.append(f"ISSUE:{cat_token}")
                elif reason_token:
                    tags.append(f"ISSUE:{reason_token}")

    return tags


def format_proxy_name(template: str, proxy: Proxy) -> str:
    """
    Safely formats a proxy name based on a template string.

    This function is robust against missing data (like no country or latency)
    and cleans up the resulting string to avoid ugly artifacts.

    Available variables:
    - {remarks}: The original remarks/name of the proxy.
    - {protocol}: e.g., 'vless', 'trojan'
    - {country}: e.g., 'US', 'NL'
    - {country_code}: e.g., 'US', 'NL'
    - {country_flag}: e.g., '🇺🇸', '🇳🇱' (emoji flag)
    - {city}: e.g., 'New York' (if available)
    - {latency}: e.g., '120'
    - {asn}: e.g., 'AS15169'
    - {address}: The proxy address (IP or domain)
    - {port}: The proxy port
    - {id}: The proxy ID (full)
    - {id_short}: The proxy ID (first 6 chars)
    """

    # 1. Get the original name, falling back to address:port if empty/generic
    original_name = proxy.remarks
    if not original_name or original_name.lower() in ["defaultproxyname", "none", ""]:
        original_name = f"{proxy.address}:{proxy.port}"

    # 2. Create a dictionary of all possible values
    cc = (proxy.country_code or "").upper()
    city = (proxy.city or "").strip()
    if city:
        city = city.replace(" ", "_")
    flag = get_flag_emoji(cc)
    geo = f"{flag}-{city}" if city else flag
    stack = build_proxy_stack(proxy)
    status_tag = "UP" if proxy.is_working else "DOWN"
    process_tag = (proxy.process or "native").upper()
    latency_tag = f"{int(proxy.latency)}ms" if proxy.latency is not None else ""
    issue_tag = ""
    if proxy.security_issues and isinstance(proxy.security_issues, dict):
        issue_tokens: List[str] = []
        for category, entries in proxy.security_issues.items():
            if not entries:
                continue
            cat_token = _normalize_token(str(category)).upper()
            for reason in entries:
                reason_token = _normalize_token(str(reason))
                if cat_token and cat_token not in ("POLICY",):
                    issue_tokens.append(
                        f"{cat_token}:{reason_token}" if reason_token else cat_token
                    )
                elif reason_token:
                    issue_tokens.append(reason_token)
        if issue_tokens:
            issue_tag = f"SEC:{','.join(sorted(set(issue_tokens)))}"

    proxy_data = {
        "remarks": original_name,
        "protocol": proxy.protocol.upper() if proxy.protocol else "",
        "stack": stack,
        "transport": _transport_label(
            proxy.details or {}, (proxy.protocol or "").lower()
        ),
        "security": _security_label(proxy.details or {}),
        "status": status_tag,
        "status_tag": status_tag,
        "process": process_tag,
        "process_tag": process_tag,
        "latency_tag": latency_tag,
        "issue_tag": issue_tag,
        "geo": geo,
        "country": proxy.country_code or proxy.country,
        "country_code": cc,
        "country_flag": get_flag_emoji(cc),
        "city": proxy.city,
        "latency": str(int(proxy.latency)) if proxy.latency is not None else None,
        "asn": proxy.asn,
        "address": proxy.address,
        "port": str(proxy.port),
        "id": proxy.id,
        "id_short": proxy.id[:6] if proxy.id else "",
    }

    try:
        # 3. Use FmtWrapper to safely substitute values.
        # This creates a dict with only non-None, non-empty values.
        safe_data = FmtWrapper({k: v for k, v in proxy_data.items() if v is not None})
        new_name = template.format_map(safe_data)

        # 4. Robust cleanup of artifacts from missing data

        # Remove empty brackets/parentheses: "[]", "()", "{}"
        new_name = re.sub(r"\[\s*\]", "", new_name)
        new_name = re.sub(r"\(\s*\)", "", new_name)
        new_name = re.sub(r"\{\s*\}", "", new_name)

        # Remove duplicate separators: " - - " -> " - "
        # This handles space, tab, hyphen, underscore, and pipe.
        new_name = re.sub(r"([ \t\-_|])\1+", r"\1", new_name)

        # Remove separators dangling at the start/end
        new_name = new_name.strip(" \t\n\r_-|")

        # Consolidate all whitespace to a single space
        new_name = re.sub(r"\s+", " ", new_name).strip()

        # If the name is empty after cleanup, return original name
        return new_name if new_name else original_name

    except (ValueError, KeyError) as e:
        logger.warning(
            f"Could not format name template '{template}' for proxy {original_name}: {e}"
        )
        return original_name  # Return original name on any failure


class ProxyTagger:
    """
    Applies a naming template to a list of Proxy objects in-place.
    Ensures unique names to avoid client conflicts (e.g., Sing-box tag collisions).
    """

    # Default template when RENAME_TEMPLATE env var is not set
    DEFAULT_TEMPLATE = (
        "{geo} | {stack} | {latency_tag} | {status_tag} | {process_tag} | {issue_tag}"
    )

    def __init__(self, name_template: Optional[str] = None):
        """
        Initializes the tagger with a name template.

        Args:
            name_template: A Python format string, e.g.,
                           "[{country}] {protocol} - {latency}ms"
                           If None, uses DEFAULT_TEMPLATE.
        """
        self.template = name_template or self.DEFAULT_TEMPLATE

    def apply(self, proxies: List[Proxy]) -> List[Proxy]:
        """
        Applies renaming to a list of proxies in place.
        Ensures all names are unique by appending a counter for duplicates.

        Returns:
            The same list of proxies, with their 'remarks' field modified.
        """
        if not self.template:
            logger.debug("No name_template provided, skipping renaming.")
            return proxies  # Do nothing if no template is set

        logger.info(
            f"Applying name template '{self.template}' to {len(proxies)} proxies..."
        )

        for proxy in proxies:
            # Format the name using the template
            new_name = format_proxy_name(self.template, proxy)

            # Modify the 'remarks' field IN-PLACE
            proxy.remarks = new_name
            # Update tags with structured metadata
            tags = build_proxy_tags(proxy)
            if proxy.tags:
                for tag in proxy.tags:
                    if tag not in tags:
                        tags.append(tag)
            proxy.tags = tags

        logger.info(f"Tagged {len(proxies)} proxies with template metadata")
        return proxies
