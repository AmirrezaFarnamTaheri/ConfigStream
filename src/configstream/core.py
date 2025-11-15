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
# Stricter pattern: match country codes only when they appear in clear isolation contexts
# Matches: [US], (DE), -FR-, _JP_, #CN, ::KR, or at the very end like "...US" or "...::US"
# This avoids matching "By" in "[By EbraSha]" because it's followed by more text
_CODE_PATTERN = re.compile(
    r"(?:"
    r"\[([A-Z]{2})\]|"  # [US]
    r"\(([A-Z]{2})\)|"  # (US)
    r"[\-_#:]([A-Z]{2})[\-_#:]|"  # -US-, _US_, #US#, ::US::
    r"[\-_#:]([A-Z]{2})$|"  # -US, _US, #US, ::US at end
    r"^([A-Z]{2})[\-_#:\s]|"  # US-, US_, US#, US:: at start
    r"::([A-Z]{2})(?:\s|$)"  # ::US (common in subscription tags)
    r")",
    flags=re.IGNORECASE,
)

# Common English two-letter words that should not be interpreted as country codes
# These will be checked even if they match the pattern above
_EXCLUDED_CODES = {
    "BY",
    "IN",
    "ON",
    "OR",
    "AS",
    "IS",
    "IT",
    "AM",
    "NO",
    "AT",
    "TO",
    "OF",
    "IF",
    "SO",
    "AN",
    "BE",
    "DO",
    "GO",
    "HE",
    "ME",
    "MY",
    "UP",
    "WE",
}


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
    """
    Infer country from remarks using flag emojis or country codes.

    Uses strict pattern matching to avoid false positives from common English words.
    """
    if not remarks:
        return None

    # First, try flag emoji detection (most reliable)
    flag_match = _FLAG_PATTERN.search(remarks)
    if flag_match:
        code = _flag_to_country_code(flag_match.group())
        if code:
            payload = _country_payload_from_code(code)
            if payload:
                return payload

    # Then try 2-letter code detection with strict context requirements
    code_match = _CODE_PATTERN.search(remarks.upper())
    if code_match:
        # Extract the matched code from whichever capture group matched
        # (the regex has multiple alternatives with different capture groups)
        candidate_code = None
        for group in code_match.groups():
            if group is not None:
                candidate_code = group
                break

        if not candidate_code:
            return None

        # Exclude common English words that happen to be valid country codes
        # Our stricter pattern should already prevent most false positives,
        # but we double-check here for extra safety
        if candidate_code in _EXCLUDED_CODES:
            # Even with strict pattern, skip codes that are common English words
            # unless they're in very clear country-code contexts
            full_match = code_match.group(0)
            # Only allow if it's in brackets or has multiple delimiters
            if not (
                full_match.startswith("[")
                or full_match.startswith("(")
                or full_match.count("-") >= 2
                or full_match.count("_") >= 2
            ):
                return None

        payload = _country_payload_from_code(candidate_code)
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

        logger.debug("Unknown protocol in config: %s...", config_string[:50])
        return None

    except Exception as e:
        logger.debug("Error parsing config '%s...': %s", config_string[:50], e)
        return None


def parse_config_batch(config_strings: list[str]) -> list[Proxy]:
    parsed = []
    for config_string in config_strings:
        proxy = parse_config(config_string)
        if proxy is not None:
            parsed.append(proxy)
    return parsed


async def geolocate_proxy(proxy: Proxy, geoip_reader: Any | None = None) -> Proxy:
    """
    Geolocate a proxy using IP-based lookup (preferred) or remarks as fallback.

    Priority order (from most to least reliable):
    1. IP-based GeoIP database lookup
    2. IP-based HTTP API fallback
    3. Remark-based inference (flags, country codes)
    4. Pre-filled country_code (if already set)

    Ensures country, country_code, city, and asn always come from the same source.
    """

    # Store original values for conflict detection
    original_country_code = proxy.country_code

    # Try IP-based geolocation first (most reliable)
    geo_data = None

    # 1. Try local GeoIP database
    if geoip_reader:
        try:
            response = geoip_reader.city(proxy.address)
            country_obj = getattr(response, "country", None)
            city_obj = getattr(response, "city", None)
            traits_obj = getattr(response, "traits", None)
            asn_obj = getattr(response, "autonomous_system", None)

            country_code = (getattr(country_obj, "iso_code", None) or "XX").upper()
            country_name = COUNTRY_NAMES.get(
                country_code, getattr(country_obj, "name", None) or "Unknown"
            )
            city_name = getattr(city_obj, "name", None) or "Unknown"

            asn_number = getattr(traits_obj, "autonomous_system_number", None)
            if asn_number is None:
                asn_number = getattr(asn_obj, "autonomous_system_number", None)
            asn = f"AS{asn_number}" if asn_number else "AS0"

            geo_data = {
                "country_code": country_code,
                "country": country_name,
                "city": city_name,
                "asn": asn,
                "source": "geoip_db",
            }
        except Exception:  # pragma: no cover
            logger.debug("GeoIP DB lookup failed for %s", proxy.address)

    # 2. If DB lookup failed, try HTTP-based lookup
    if not geo_data:
        http_result = await _lookup_geoip_http(proxy.address)
        if http_result:
            country_code = http_result.get("country_code", "XX")
            # Normalize country name using our mapping
            country = COUNTRY_NAMES.get(country_code, http_result.get("country", "Unknown"))
            geo_data = {
                "country_code": country_code,
                "country": country,
                "city": http_result.get("city", "Unknown"),
                "asn": http_result.get("asn", "AS0"),
                "source": "http_api",
            }

    # If IP-based lookup succeeded, use it
    if geo_data:
        # Log conflicts for debugging/tuning
        if (
            original_country_code
            and original_country_code != "XX"
            and original_country_code != geo_data["country_code"]
        ):
            logger.debug(
                "Geolocation conflict for %s: pre-filled=%s, IP-based=%s (using IP-based), remarks=%s",
                proxy.address,
                original_country_code,
                geo_data["country_code"],
                proxy.remarks[:50] if proxy.remarks else "",
            )

        proxy.country_code = geo_data["country_code"]
        proxy.country = geo_data["country"]
        proxy.city = geo_data["city"]
        proxy.asn = geo_data["asn"]
        return proxy

    # 3. Fallback: try to infer from remarks (less reliable)
    inferred = _infer_country_from_remarks(proxy.remarks)
    if inferred:
        proxy.country = inferred["country"]
        proxy.country_code = inferred["country_code"]
        # Leave city/asn as-is or set to unknown since we can't infer them from remarks
        if not proxy.city or proxy.city == "":
            proxy.city = "Unknown"
        if not proxy.asn or proxy.asn == "":
            proxy.asn = "AS0"
        return proxy

    # 4. Fallback: if country_code was pre-filled, ensure country name is consistent
    if proxy.country_code and proxy.country_code != "XX":
        proxy.country = COUNTRY_NAMES.get(proxy.country_code, proxy.country or "Unknown")
        if not proxy.city or proxy.city == "":
            proxy.city = "Unknown"
        if not proxy.asn or proxy.asn == "":
            proxy.asn = "AS0"
        return proxy

    # 5. Last resort: mark as unknown
    proxy.country = "Unknown"
    proxy.country_code = "XX"
    proxy.city = "Unknown"
    proxy.asn = "AS0"

    return proxy
