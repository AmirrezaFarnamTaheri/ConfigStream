# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import logging
import re
from urllib.parse import urlparse
from typing import List, Tuple, Dict, Any, Optional

from .decoders import safe_b64_decode, validate_b64_input
from ..constants import (
    MAX_CONFIG_LINE_LENGTH,
    MAX_LINES_PER_SOURCE,
    VALID_PROTOCOLS,
    MAX_B64_OUTPUT_SIZE,
    MAX_B64_INPUT_SIZE,
    BLOCKED_DOMAINS,
)
from ..security_validator import SecurityValidator

logger = logging.getLogger(__name__)

# Enhanced to support Hex (0x...) and Octal (0...) formats
_IPV4_PORT_PATTERN = re.compile(
    r"\b(?P<host>(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3})|(?:0x[0-9a-fA-F]+)|(?:0[0-7]+)):(?P<port>\d{1,5})\b"
)
_IPV6_PORT_PATTERN = re.compile(r"\[(?P<host>[0-9A-Fa-f:]+)\]:(?P<port>\d{1,5})")


def is_plausible_proxy_config(config: str) -> bool:
    """Basic plausibility check for proxy configuration."""
    # OpenVPN support
    if config.startswith("-----BEGIN CERTIFICATE"):
        return True
    if "client" in config and ("dev tun" in config or "dev tap" in config):
        return True

    # Filter subscription URLs (not proxy configs)
    config_lower = config.lower()
    if config_lower.startswith("https://") or config_lower.startswith("http://"):
        if "@" not in config and any(d in config_lower for d in BLOCKED_DOMAINS):
            parsed = urlparse(config)
            # Allow direct proxies even on blocked domains when clearly host:port only.
            if (
                parsed.hostname
                and parsed.port
                and parsed.path in ("", "/")
                and not parsed.query
                and not parsed.fragment
            ):
                return True
            return False
    return True


def extract_config_lines(
    payload_str: str,
    max_lines: int = MAX_LINES_PER_SOURCE,
    source_url: str = "",
) -> Tuple[List[str], Dict[str, Any]]:
    """
    Extract potential proxy configuration lines from raw payload string.
    Handles Base64, JSON (V2Ray/Sing-box), YAML (Clash), and raw lines.
    """
    drop_stats: Dict[str, int] = {}

    if not payload_str:
        return [], {}

    # 1. Check for JSON (V2Ray / Sing-box / Shadowsocks-Rust)
    if payload_str.strip().startswith("{") and payload_str.strip().endswith("}"):
        try:
            # Try to load as JSON
            data = json.loads(payload_str)
            # If standard V2Ray, return as is
            return [payload_str], {}
        except Exception:
            return [payload_str], {}  # Let parser fail later if invalid

    # 2. Check for YAML (Clash)
    elif (
        "proxies:" in payload_str
        and (
            "- name:" in payload_str
            or "-name:" in payload_str
            or "- type:" in payload_str
        )
        or (
            source_url and (source_url.endswith(".yaml") or source_url.endswith(".yml"))
        )
    ):
        try:
            import yaml  # type: ignore

            data = yaml.safe_load(payload_str)
            # Handle list of proxies
            proxies = data if isinstance(data, list) else data.get("proxies", [])

            if isinstance(proxies, list):
                return [json.dumps(p) for p in proxies if isinstance(p, dict)], {}
        except ImportError:
            logger.warning("PyYAML not installed, skipping Clash YAML parsing")
            drop_stats["missing_dependency_yaml"] = 1
        except Exception as e:
            logger.debug(f"Failed to parse Clash YAML: {e}")
            drop_stats["yaml_parse_error"] = 1

        if "proxies" not in payload_str:
            lines = payload_str.splitlines()
        else:
            return [payload_str], drop_stats

    # 3. OpenVPN
    elif "client" in payload_str and (
        "dev tun" in payload_str or "dev tap" in payload_str
    ):
        if MAX_B64_OUTPUT_SIZE <= 0 or len(payload_str) < MAX_B64_OUTPUT_SIZE:
            return [payload_str], {}
        else:
            return [], {"size_limit_exceeded": 1}

    else:
        # Attempt Base64 decode for subscriptions
        decoded = safe_b64_decode(payload_str)
        if decoded is None:
            # Fallback for plain text lists
            lines = payload_str.splitlines()
        else:
            lines = decoded.splitlines()

    if max_lines > 0 and len(lines) > max_lines:
        original_count = len(lines)
        logger.warning(
            f"Payload has {original_count} lines, truncating to {max_lines}."
        )
        lines = lines[:max_lines]
        drop_stats["truncated_lines"] = original_count - max_lines

    valid_prefixes = {p for p in VALID_PROTOCOLS if not p.endswith("://")}
    valid_prefixes.update({p + "://" for p in VALID_PROTOCOLS})

    configs = []
    dropped_samples: List[str] = []

    default_scheme = "http://"
    if source_url:
        u_lower = source_url.lower()
        if "socks5" in u_lower:
            default_scheme = "socks5://"
        elif "socks4" in u_lower:
            default_scheme = "socks4://"

    html_drops = 0

    for line in lines:
        candidate = line.strip()
        if not candidate:
            continue
        if candidate.startswith("#"):
            continue

        # Individual HTML Line Detection
        if candidate.startswith("<") and (
            candidate.lower().startswith("<!doctype")
            or candidate.lower().startswith("<html")
            or candidate.lower().startswith("<head")
            or candidate.lower().startswith("<body")
            or candidate.lower().startswith("<div")
            or candidate.lower().startswith("<script")
            or candidate.lower().startswith("<span")
        ):
            html_drops += 1
            continue

        if MAX_CONFIG_LINE_LENGTH > 0 and len(candidate) > MAX_CONFIG_LINE_LENGTH:
            continue

        if candidate.startswith("{"):
            configs.append(candidate)
            continue

        parts = candidate.split("://", 1)
        reason = ""

        if len(parts) == 2:
            protocol = parts[0]
            if protocol not in valid_prefixes:
                reason = "invalid_protocol"
            elif not is_plausible_proxy_config(candidate):
                reason = "implausible_format"
        else:
            raw_candidate = candidate
            match = _IPV6_PORT_PATTERN.search(candidate)
            if not match:
                match = _IPV4_PORT_PATTERN.search(candidate)

            if match:
                host = match.group("host")
                port_str = match.group("port")
                try:
                    port_val = int(port_str)
                except (TypeError, ValueError):
                    reason = "invalid_port"
                else:
                    if not (1 <= port_val <= 65535):
                        reason = "invalid_port"
                    else:
                        addr = f"[{host}]" if ":" in host else host
                        candidate = f"{default_scheme}{addr}:{port_val}"

                        if ":" not in host:
                            prefix = match.group(0)
                            raw_trim = raw_candidate.strip()

                            if raw_trim.startswith(prefix + ":"):
                                tail = raw_trim[len(prefix) + 1 :]
                                cred_parts = tail.split(":")
                                if len(cred_parts) >= 2:
                                    user = cred_parts[0].strip()
                                    pwd = cred_parts[1].strip()
                                    if (
                                        user
                                        and pwd
                                        and " " not in user
                                        and " " not in pwd
                                        and len(user) <= 128
                                        and len(pwd) <= 128
                                    ):
                                        candidate = f"{default_scheme}{user}:{pwd}@{host}:{port_val}"

                            elif raw_trim.endswith("@" + prefix):
                                head = raw_trim[: -len("@" + prefix)]
                                if ":" in head:
                                    user, pwd = head.split(":", 1)
                                    user = user.strip()
                                    pwd = pwd.strip()
                                    if (
                                        user
                                        and pwd
                                        and " " not in user
                                        and " " not in pwd
                                        and len(user) <= 64
                                        and len(pwd) <= 128
                                    ):
                                        scheme = (
                                            "ss://"
                                            if "chacha" in user
                                            or "aes" in user
                                            or "rc4" in user
                                            else default_scheme
                                        )
                                        candidate = (
                                            f"{scheme}{user}:{pwd}@{host}:{port_val}"
                                        )

                        if not is_plausible_proxy_config(candidate):
                            reason = "implausible_format"
            else:
                reason = "missing_protocol_separator"

        if not reason:
            configs.append(candidate)
        else:
            drop_stats[reason] = drop_stats.get(reason, 0) + 1
            if len(dropped_samples) < 5:
                sample = f"{candidate[:50]}... [{reason}]"
                dropped_samples.append(SecurityValidator.sanitize_log_message(sample))

    if html_drops > 0:
        drop_stats["html_content"] = html_drops

    total_dropped = sum(drop_stats.values())
    if total_dropped > 0:
        total_seen = total_dropped + len(configs)
        drop_rate = (total_dropped / total_seen) if total_seen else 1.0
        if html_drops > total_dropped * 0.9:
            safe_source = (
                SecurityValidator.sanitize_log_message(source_url)
                if source_url
                else "unknown"
            )
            logger.debug(
                f"Source {safe_source} dropped {html_drops} lines of HTML content."
            )
        else:
            log_method = logger.warning if drop_rate > 0.5 else logger.debug
            if len(configs) > 0:
                log_method(
                    f"Parsed {len(configs)} configs. Dropped {total_dropped} lines. "
                    f"Reasons: {drop_stats}"
                )
            else:
                all_missing_sep = (
                    drop_stats.get("missing_protocol_separator", 0) == total_dropped
                )
                method = logger.debug if all_missing_sep else log_method
                method(
                    f"All lines dropped. Reasons: {drop_stats}. Samples: {dropped_samples}"
                )

    return configs, drop_stats
