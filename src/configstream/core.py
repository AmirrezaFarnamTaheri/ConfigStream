import logging
import re
from typing import Any, Callable, Dict, Optional

import httpx
from .http_client import get_client

from .parsers import (
    _parse_brook,
    _parse_generic_url_scheme,
    _parse_hysteria,
    _parse_hysteria2,
    _parse_juicity,
    _parse_naive,
    _parse_snell,
    _parse_ss,
    _parse_ss2022,
    _parse_ssr,
    _parse_trojan,
    _parse_tuic,
    _parse_v2ray_json,
    _parse_vless,
    _parse_vmess,
    _parse_wireguard,
    _parse_xray,
)

from .models import Proxy
from .countries import COUNTRY_NAMES

logger = logging.getLogger(__name__)


_FLAG_PATTERN = re.compile(r"[\U0001F1E6-\U0001F1FF]{2}")
_CODE_PATTERN = re.compile(r"(?<![A-Z0-9])([A-Z]{2})(?![A-Z0-9])")


def _flag_to_country_code(flag: str) -> Optional[str]:
    if len(flag) != 2:
        return None
    code_points = [ord(char) - 0x1F1E6 + ord("A") for char in flag]
    if any(point < ord("A") or point > ord("Z") for point in code_points):
        return None
    return "".join(chr(point) for point in code_points)


def _country_payload_from_code(code: str) -> Optional[Dict[str, str]]:
    code = code.upper()
    if code not in COUNTRY_NAMES:
        return None
    return {"country_code": code, "country": COUNTRY_NAMES[code]}


def _infer_country_from_remarks(remarks: str) -> Optional[Dict[str, str]]:
    if not remarks:
        return None

    flag_match = _FLAG_PATTERN.search(remarks)
    if flag_match:
        code = _flag_to_country_code(flag_match.group())
        if code:
            payload = _country_payload_from_code(code)
            if payload:
                return payload

    code_match = _CODE_PATTERN.search(remarks.upper())
    if code_match:
        payload = _country_payload_from_code(code_match.group(1))
        if payload:
            return payload

    return None


async def _lookup_geoip_http(
    address: str, timeout_seconds: float = 5.0
) -> Optional[Dict[str, Any]]:
    if not address:
        return None

    try:
        async with get_client() as client:
            url = f"http://ip-api.com/json/{address}?fields=status,country,countryCode,city,as"
            response = await client.get(url, timeout=timeout_seconds)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    if not isinstance(payload, dict) or payload.get("status") != "success":
        return None

    asn_value = payload.get("as") or ""
    asn = None
    if isinstance(asn_value, str):
        parts = asn_value.split()
        if parts and parts[0].startswith("AS"):
            asn = parts[0]

    return {
        "country": payload.get("country") or "Unknown",
        "country_code": payload.get("countryCode") or "XX",
        "city": payload.get("city") or "Unknown",
        "asn": asn or "AS0",
    }


ParserFunc = Callable[[str], Optional[Proxy]]


def _create_parser_map() -> Dict[str, ParserFunc]:
    """Create a mapping from protocol prefixes to parser functions."""
    return {
        "vmess://": _parse_vmess,
        "vless://": _parse_vless,
        "ss://": _parse_ss,
        "ss2022://": _parse_ss2022,
        "ssr://": _parse_ssr,
        "trojan://": _parse_trojan,
        "hysteria://": _parse_hysteria,
        "hy2://": _parse_hysteria2,
        "hysteria2://": _parse_hysteria2,
        "tuic://": _parse_tuic,
        "wg://": _parse_wireguard,
        "wireguard://": _parse_wireguard,
        "naive+https://": _parse_naive,
        "xray://": _parse_xray,
        "xtls://": _parse_xray,
        "snell://": _parse_snell,
        "brook://": _parse_brook,
        "juicity://": _parse_juicity,
    }


# Pre-compute the parser map at module load time for efficiency
_parser_map = _create_parser_map()
_generic_protocols = {"ssh", "http", "https", "socks", "socks4", "socks5"}


def parse_config(config_string: str) -> Proxy | None:
    """
    Parse a proxy configuration string and return a Proxy object.

    This function uses a dispatch table for efficient protocol matching.
    """
    if not config_string or not isinstance(config_string, str):
        return None

    config_string = config_string.strip()
    if not config_string or config_string.startswith("#"):
        return None

    try:
        # Fast path for common protocols using the pre-computed map
        for prefix, parser in _parser_map.items():
            if config_string.startswith(prefix):
                return parser(config_string)

        # Special case for JSON-based V2Ray configs
        if config_string.lstrip().startswith("{"):
            return _parse_v2ray_json(config_string)

        # Fallback for generic URL-based schemes
        if "://" in config_string:
            protocol = config_string.split("://", 1)[0]
            if protocol in _generic_protocols:
                return _parse_generic_url_scheme(config_string)

        logger.debug(f"Unknown protocol in config: {config_string[:50]}...")
        return None

    except Exception as e:
        logger.debug(f"Error parsing config '{config_string[:50]}...': {e}")
        return None


def parse_config_batch(config_strings: list[str]) -> list[Proxy]:
    parsed = []
    for config_string in config_strings:
        proxy = parse_config(config_string)
        if proxy is not None:
            parsed.append(proxy)
    return parsed


async def geolocate_proxy(proxy: Proxy, geoip_reader: Any | None = None) -> Proxy:
    """Geolocate a proxy using remarks, a local DB, or a fallback HTTP lookup."""

    # 1. If country code is valid, ensure country name is consistent.
    if proxy.country_code and proxy.country_code != "XX":
        if not proxy.country or proxy.country == "Unknown":
            payload = _country_payload_from_code(proxy.country_code)
            if payload:
                proxy.country = payload["country"]
        return proxy

    # 2. Try to infer from remarks (e.g., flags, country codes).
    inferred = _infer_country_from_remarks(proxy.remarks)
    if inferred:
        proxy.country = inferred["country"]
        proxy.country_code = inferred["country_code"]
        return proxy

    # 3. Use the local GeoIP database if available.
    if geoip_reader:
        try:
            response = geoip_reader.city(proxy.address)
            proxy.country = response.country.name or "Unknown"
            proxy.country_code = response.country.iso_code or "XX"
            proxy.city = response.city.name or "Unknown"
            if response.autonomous_system.autonomous_system_number:
                proxy.asn = f"AS{response.autonomous_system.autonomous_system_number}"
            return proxy
        except Exception:  # pragma: no cover
            logger.debug(f"GeoIP DB lookup failed for {proxy.address}")

    # 4. Fallback to an external HTTP-based lookup.
    http_result = await _lookup_geoip_http(proxy.address)
    if http_result:
        proxy.country = http_result.get("country", "Unknown")
        proxy.country_code = http_result.get("country_code", "XX")
        proxy.city = http_result.get("city", "Unknown")
        proxy.asn = http_result.get("asn", "AS0")
    else:
        proxy.country = "Unknown"
        proxy.country_code = "XX"
        proxy.city = "Unknown"
        proxy.asn = "AS0"

    return proxy
