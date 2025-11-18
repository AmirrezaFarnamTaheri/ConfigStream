import logging
import re
from typing import Callable, Dict, Optional

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
    r"\[(?P<cc1>[A-Z]{2})\]|"  # [US]
    r"\((?P<cc2>[A-Z]{2})\)|"  # (US)
    r"[\-_#:](?P<cc3>[A-Z]{2})[\-_#:]|"  # -US-, _US_, #US#, ::US::
    r"[\-_#:](?P<cc4>[A-Z]{2})(?=$)|"  # -US, _US, #US, ::US at end (true end)
    r"(?:(?<=^)|(?<=\s))(?P<cc5>[A-Z]{2})(?=[\-_#:\s])|"  # boundary before code
    r"::(?P<cc6>[A-Z]{2})(?:\s|$)"  # ::US (common in subscription tags)
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
        candidate_code = (
            code_match.group("cc1")
            or code_match.group("cc2")
            or code_match.group("cc3")
            or code_match.group("cc4")
            or code_match.group("cc5")
            or code_match.group("cc6")
        )

        if not candidate_code:
            return None

        candidate_code = candidate_code.upper()
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

        # If no prefix matched, try the auto-detection engine as a last resort
        from .auto_detect import auto_detect_and_parse

        return auto_detect_and_parse(config_string)

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
