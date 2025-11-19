import logging
from typing import Callable, Dict, Optional

from .models import Proxy
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

logger = logging.getLogger(__name__)


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
