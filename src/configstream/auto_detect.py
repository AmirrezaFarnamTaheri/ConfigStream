# SPDX-License-Identifier: AGPL-3.0-or-later
"""Protocol auto-detection for proxy configurations."""

import binascii
import json
import logging
from typing import Optional, Protocol, cast
from urllib.parse import urlparse

from .models import Proxy
from .security_validator import _safe_log_text
from .constants import VWARP_SOCKS5_PORT
from .parsers import (
    parse_generic_url_scheme,
    parse_hysteria,
    parse_hysteria2,
    parse_naive,
    parse_ss,
    parse_trojan,
    parse_tuic,
    parse_vmess,
    parse_vless,
    parse_wireguard,
    parse_openvpn,
    parse_xray,
    parse_snell,
    parse_brook,
    parse_juicity,
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

    # Try OpenVPN first (content based)
    if "client" in config and ("dev tun" in config or "dev tap" in config):
        try:
            result = parse_openvpn(config)
            if result:
                return result
        except Exception:  # nosec
            pass

    # Try Naked IP:PORT
    if "://" not in config and ":" in config and not config.startswith("{"):
        res = parse_generic_url_scheme(config)
        if res:
            return res

    # Try URL-based detection first
    if "://" in config:
        scheme = config.split("://")[0].lower()

        # Map common schemes to parsers
        parser_map = cast(
            dict[str, ParserCallable],
            {
                "vmess": parse_vmess,
                "vless": parse_vless,
                "ss": parse_ss,
                "shadowsocks": parse_ss,
                "trojan": parse_trojan,
                "hysteria": parse_hysteria,
                "hy2": parse_hysteria2,
                "hysteria2": parse_hysteria2,
                "tuic": parse_tuic,
                "wg": parse_wireguard,
                "wireguard": parse_wireguard,
                # Map exclave to wireguard parser
                "exclave": parse_wireguard,
                "http": parse_generic_url_scheme,
                "https": parse_generic_url_scheme,
                "socks": parse_generic_url_scheme,
                "socks4": parse_generic_url_scheme,
                "socks5": parse_generic_url_scheme,
                "ssh": lambda x: parse_generic_url_scheme(
                    x
                ),  # SSH often works with generic
                "naive": parse_naive,
                "naive+https": parse_naive,
                "naive+http": parse_naive,
                "xray": parse_xray,
                "snell": parse_snell,
                "brook": parse_brook,
                "juicity": parse_juicity,
            },
        )

        if scheme in parser_map:
            try:
                result = parser_map[scheme](config)
                if result:
                    return result
            except (ValueError, KeyError, binascii.Error, json.JSONDecodeError) as exc:
                logger.debug(f"Parser {scheme} failed: {_safe_log_text(exc)}")

    # Try JSON parsing (V2Ray JSON or Clash JSON format)
    if config.startswith("{"):
        try:
            from .parsers import parse_v2ray_json

            result = parse_v2ray_json(config)
            if result:
                return result
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            logger.debug(f"v2ray json parser skipped: {_safe_log_text(exc)}")

        try:
            from .parsers.clash_json import parse_clash_json

            result = parse_clash_json(config)
            if result:
                return result
        except Exception as exc:
            logger.debug(f"clash json parser skipped: {_safe_log_text(exc)}")

    # Port-based heuristics
    try:
        if "://" in config:
            parsed = urlparse(config)
            port = parsed.port

            # Common port numbers suggest protocols
            if port in [443, 8443]:  # HTTPS/TLS ports
                # Likely Trojan or VLESS with TLS
                tls_candidate_parsers: tuple[ParserCallable, ...] = (
                    parse_trojan,
                    parse_vless,
                )

                for parser in tls_candidate_parsers:
                    try:
                        result = parser(config)
                        if result:
                            return result
                    except (ValueError, KeyError) as exc:
                        logger.debug(
                            f"TLS candidate parser {parser.__name__} skipped: {_safe_log_text(exc)}"  # type: ignore[attr-defined]
                        )
                        continue

            elif port in [1080, VWARP_SOCKS5_PORT]:  # SOCKS ports
                try:
                    return parse_generic_url_scheme(config)
                except ValueError as exc:
                    logger.debug(
                        f"SOCKS candidate parser skipped: {_safe_log_text(exc)}"
                    )

    except (ValueError, AttributeError):
        # Handles cases where urlparse fails or port is not present
        logger.debug("Port-based heuristics failed or not applicable")

    # Fallback: try all parsers
    fallback_parsers: tuple[ParserCallable, ...] = (
        parse_vmess,
        parse_vless,
        parse_ss,
        parse_trojan,
        parse_hysteria2,
        parse_hysteria,
        parse_tuic,
        parse_wireguard,
        parse_naive,
    )

    for parser in fallback_parsers:
        try:
            result = parser(config)
            if result:
                # STRICT CHECK: Reduce false positives from aggressive URL parsers
                if "://" in config:
                    scheme = config.split("://")[0].lower()

                    # If scheme looks like a protocol but parser says something else, be suspicious
                    # e.g. "http://..." parsed as hysteria2 -> suspicious

                    # Known valid schemes for fallback parsers
                    # Heuristic Rules:
                    # These parsers rely on simple URL parsing. To prevent false positives where
                    # normal HTTP URLs (e.g. "http://example.com") are misclassified as proxies,
                    # we explicitly define which schemes are valid for each protocol.
                    valid_schemes_for_parser = {
                        "hysteria2": ["hysteria2", "hy2"],
                        "hysteria": ["hysteria", "hy1"],
                        "tuic": ["tuic"],
                        "wireguard": [
                            "wireguard",
                            "wg",
                            "exclave",
                        ],  # Add exclave
                        "vmess": ["vmess"],
                        "vless": ["vless"],
                        "ss": ["ss", "ss2022"],
                        "trojan": ["trojan", "trojan-go"],
                        "naive": ["naive", "naive+https", "naive+http"],
                    }

                    # If the result protocol has specific schemes, enforce them
                    allowed = valid_schemes_for_parser.get(result.protocol)
                    if allowed:
                        if scheme not in allowed:
                            # Allow generic schemes ONLY if the parser logic explicitly supports it
                            # But Hysteria/Tuic/WireGuard parsers in this codebase are thin wrappers around urlparse
                            # so they will accept "http://google.com" as a valid config. This is WRONG.
                            logger.debug(
                                f"Rejected scheme mismatch: Protocol {result.protocol} does not support scheme {scheme}://"
                            )
                            continue

                logger.info(f"Auto-detected protocol: {result.protocol}")
                return result
        except (ValueError, KeyError, binascii.Error, json.JSONDecodeError) as exc:
            logger.debug(
                f"Fallback parser {parser.__name__} skipped: {_safe_log_text(exc)}"  # type: ignore[attr-defined]
            )
            continue

    return None
