"""Protocol auto-detection for proxy configurations."""

import binascii
import json
import logging
from pathlib import Path
from typing import Optional, Protocol, cast
from urllib.parse import urlparse

from .models import Proxy
from .plugins.loader import PluginManager
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
    _parse_openvpn,
)


class ParserCallable(Protocol):
    def __call__(self, config: str, /) -> Optional[Proxy]:
        """Callable protocol for proxy parser functions."""


logger = logging.getLogger(__name__)

# Initialize Plugin Manager
PLUGIN_DIR = Path(__file__).parent / "plugins"
PLUGIN_MANAGER = PluginManager(PLUGIN_DIR)
try:
    PLUGIN_MANAGER.load_plugins()
except Exception as e:
    logger.warning(f"Failed to load plugins: {e}")


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

    # 0. Try Plugins First (Universal Plugin System)
    try:
        plugin_result = PLUGIN_MANAGER.parse_all(config)
        if plugin_result:
            return plugin_result
    except Exception as exc:
        logger.debug(f"Plugin parsing failed: {exc}")

    # Try OpenVPN first (content based)
    if "client" in config and ("dev tun" in config or "dev tap" in config):
        try:
            result = _parse_openvpn(config)
            if result:
                return result
        except Exception:
            pass

    # Try Naked IP:PORT
    if "://" not in config and ":" in config and not config.startswith("{"):
        res = _parse_generic_url_scheme(config)
        if res:
            return res

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
                "ssh": lambda x: _parse_generic_url_scheme(
                    x
                ),  # SSH often works with generic
            },
        )

        if scheme in parser_map:
            try:
                result = parser_map[scheme](config)
                if result:
                    return result
            except (ValueError, KeyError, binascii.Error, json.JSONDecodeError) as exc:
                logger.debug(f"Parser {scheme} failed: {exc}")

    # Try JSON parsing (V2Ray JSON or Clash JSON format)
    if config.startswith("{"):
        try:
            from .parsers import _parse_v2ray_json

            result = _parse_v2ray_json(config)
            if result:
                return result
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            logger.debug(f"v2ray json parser skipped: {exc}")

        try:
            from .parsers.clash_json import parse_clash_json
            result = parse_clash_json(config)
            if result:
                return result
        except Exception as exc:
            logger.debug(f"clash json parser skipped: {exc}")

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
                            f"TLS candidate parser {parser.__name__} skipped: {exc}"  # type: ignore[attr-defined]
                        )
                        continue

            elif port in [1080, 10808]:  # SOCKS ports
                try:
                    return _parse_generic_url_scheme(config)
                except ValueError as exc:
                    logger.debug(f"SOCKS candidate parser skipped: {exc}")

    except (ValueError, AttributeError):
        # Handles cases where urlparse fails or port is not present
        logger.debug("Port-based heuristics failed or not applicable")

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
                    valid_schemes_for_parser = {
                        "hysteria2": ["hysteria2", "hy2"],
                        "hysteria": ["hysteria", "hy1"],
                        "tuic": ["tuic"],
                        "wireguard": ["wireguard", "wg"],
                        "vmess": ["vmess"],
                        "vless": ["vless"],
                        "ss": ["ss", "ss2022"],
                        "trojan": ["trojan", "trojan-go"],
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
                f"Fallback parser {parser.__name__} skipped: {exc}"  # type: ignore[attr-defined]
            )
            continue

    return None
