"""Protocol auto-detection for proxy configurations."""

import binascii
import json
import logging
from typing import Optional, Protocol, cast
from urllib.parse import urlparse

from .models import Proxy
from .parsers import (
    _parse_generic_url_scheme,
    _parse_hysteria,
    _parse_hysteria2,
    _parse_ss,
    _parse_trojan,
    _parse_tuic,
    _parse_vmess,
    _parse_vless,
    _parse_wireguard,
)


class ParserCallable(Protocol):
    def __call__(self, config: str, /) -> Optional[Proxy]:
        """Callable protocol for proxy parser functions."""


logger = logging.getLogger(__name__)


def auto_detect_and_parse(config: str) -> Optional[Proxy]:
    """
    Auto-detect protocol and parse proxy config.

    Tries multiple parsers and heuristics to parse unknown config formats.

    Args:
        config: Raw proxy configuration string

    Returns:
        Parsed proxy or None
    """
    config = config.strip()
    if not config:
        return None

    # Try URL-based detection first
    if "://" in config:
        scheme = config.split("://")[0].lower()

        # Map common schemes to parsers
        parser_map = cast(
            dict[str, ParserCallable],
            {
                "vmess": _parse_vmess,
                "vless": _parse_vless,
                "ss": _parse_ss,
                "shadowsocks": _parse_ss,
                "trojan": _parse_trojan,
                "hysteria": _parse_hysteria,
                "hy2": _parse_hysteria2,
                "hysteria2": _parse_hysteria2,
                "tuic": _parse_tuic,
                "wg": _parse_wireguard,
                "wireguard": _parse_wireguard,
                "http": _parse_generic_url_scheme,
                "https": _parse_generic_url_scheme,
                "socks": _parse_generic_url_scheme,
                "socks4": _parse_generic_url_scheme,
                "socks5": _parse_generic_url_scheme,
            },
        )

        if scheme in parser_map:
            try:
                result = parser_map[scheme](config)
                if result:
                    return result
            except (ValueError, KeyError, binascii.Error, json.JSONDecodeError) as exc:
                logger.debug("Parser %s failed: %s", scheme, exc)

    # Try JSON parsing (V2Ray JSON format)
    if config.startswith("{"):
        try:
            from .parsers import _parse_v2ray_json

            result = _parse_v2ray_json(config)
            if result:
                return result
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            logger.debug("v2ray json parser skipped: %s", exc)

    # Port-based heuristics
    try:
        if "://" in config:
            parsed = urlparse(config)
            port = parsed.port

            # Common port numbers suggest protocols
            if port in [443, 8443]:  # HTTPS/TLS ports
                # Likely Trojan or VLESS with TLS
                tls_candidate_parsers: tuple[ParserCallable, ...] = (
                    _parse_trojan,
                    _parse_vless,
                )

                for parser in tls_candidate_parsers:
                    try:
                        result = parser(config)
                        if result:
                            return result
                    except (ValueError, KeyError) as exc:
                        logger.debug(
                            "TLS candidate parser %s skipped: %s",
                            parser.__name__,  # type: ignore[attr-defined]
                            exc,
                        )
                        continue

            elif port in [1080, 10808]:  # SOCKS ports
                try:
                    return _parse_generic_url_scheme(config)
                except ValueError as exc:
                    logger.debug("SOCKS candidate parser skipped: %s", exc)

    except (ValueError, AttributeError):
        # Handles cases where urlparse fails or port is not present
        pass

    # Fallback: try all parsers
    fallback_parsers: tuple[ParserCallable, ...] = (
        _parse_vmess,
        _parse_vless,
        _parse_ss,
        _parse_trojan,
        _parse_hysteria2,
        _parse_hysteria,
        _parse_tuic,
        _parse_wireguard,
        _parse_generic_url_scheme,
    )

    for parser in fallback_parsers:
        try:
            result = parser(config)
            if result:
                logger.info(f"Auto-detected protocol: {result.protocol}")
                return result
        except (ValueError, KeyError, binascii.Error, json.JSONDecodeError) as exc:
            logger.debug(
                "Fallback parser %s skipped: %s",
                parser.__name__,  # type: ignore[attr-defined]
                exc,
            )
            continue

    return None
