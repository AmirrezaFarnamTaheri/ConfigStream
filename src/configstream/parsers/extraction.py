# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import re
from urllib.parse import urlparse
from typing import List, Tuple, Dict, Any, Optional

from .decoders import safe_b64_decode
from ..constants import (
    MAX_CONFIG_LINE_LENGTH,
    MAX_LINES_PER_SOURCE,
    VALID_PROTOCOLS,
    MAX_B64_OUTPUT_SIZE,
    MAX_B64_INPUT_SIZE,
    BLOCKED_DOMAINS,
)

logger = logging.getLogger(__name__)

_IPV4_PORT_PATTERN = re.compile(
    r"\b(?P<host>(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}):(?P<port>\d{1,5})\b"
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

    if "://" not in config:
        return False
    protocol, rest = config.split("://", 1)
    if not protocol or len(protocol) > 20 or len(rest) < 4:
        return False

    # Relax noise check (allowed up to 98% special chars for base64 heavy VLESS)
    special_char_count = sum(
        1 for c in rest if not c.isalnum() and c not in ":-_./@#%?&=+,;()~[]!*'|$"
    )

    if len(rest) > 20 and special_char_count > len(rest) * 0.98:
        return False

    # [Check] Double protocol
    if "://" in rest:
        if "http://" in rest or "https://" in rest:
            if "?" in rest:
                _, query = rest.split("?", 1)
                if "://" in query and "=" not in query.split("://")[0][-10:]:
                    return False
    return True


def extract_config_lines(
    payload: Any,
    max_lines: int = MAX_LINES_PER_SOURCE,
    source_url: Optional[str] = None,
) -> Tuple[List[str], Dict[str, int]]:
    """
    Extract configuration lines with validation and limits.

    Args:
        payload: Content to parse (str or bytes).
        max_lines: Max number of lines to process.
        source_url: The URL where payload came from (used for protocol inference).

    Returns:
        Tuple[List[str], Dict[str, int]]: A tuple containing the list of valid config lines
        and a dictionary of drop reasons (count by reason).
    """
    drop_stats: Dict[str, int] = {}

    # CRITICAL: Pre-check size to prevent OOM on massive files
    if (
        MAX_B64_INPUT_SIZE > 0
        and hasattr(payload, "__len__")
        and len(payload) > MAX_B64_INPUT_SIZE
    ):
        logger.warning(
            f"extract_config_lines: Payload exceeds {MAX_B64_INPUT_SIZE} bytes limit. Dropping to prevent OOM."
        )
        return [], {"size_limit_exceeded": 1}

    # Handle input type (bytes or str)
    if isinstance(payload, bytes):
        try:
            payload_str = payload.decode("utf-8")
        except UnicodeDecodeError:
            try:
                payload_str = payload.decode("latin-1")
            except Exception:
                payload_str = payload.decode("utf-8", errors="ignore")
                logger.debug(
                    "extract_config_lines: Binary payload decoded with errors ignored."
                )
    elif isinstance(payload, str):
        payload_str = payload
    else:
        logger.debug(f"extract_config_lines: Invalid payload type {type(payload)}.")
        return [], {"invalid_type": 1}

    if not payload_str.strip():
        return [], {"empty_payload": 1}

    # 1. Check for JSON Array (e.g. ["vmess://...", ...])
    if payload_str.strip().startswith("["):
        try:
            import json

            data = json.loads(payload_str)
            if isinstance(data, list):
                # Extract strings from list
                configs = []
                for item in data:
                    if isinstance(item, str):
                        configs.append(item)
                    elif isinstance(item, dict):
                        # Maybe object with config string? or V2Ray object?
                        # For now, if dict, convert to JSON string (V2Ray format)
                        configs.append(json.dumps(item))
                # Validate extracted configs later in loop
                # We replace lines with extracted list
                lines = configs
            else:
                # Not a list, maybe fallback
                lines = payload_str.splitlines()
        except Exception as e:
            logger.debug(f"Failed to parse JSON array: {e}")
            lines = payload_str.splitlines()

    # 2. Check for V2Ray JSON Object (single)
    elif payload_str.strip().startswith("{"):
        # Check if it's V2Ray (outbounds) or just a JSON object wrapper
        try:
            import json

            data = json.loads(payload_str)
            # If it has "proxies" key (Clash/Mihomo JSON)
            if "proxies" in data and isinstance(data["proxies"], list):
                return [
                    json.dumps(p) for p in data["proxies"] if isinstance(p, dict)
                ], {}
            # If standard V2Ray, return as is
            return [payload_str], {}
        except Exception:
            return [payload_str], {}  # Let parser fail later if invalid

    # 3. Check for YAML (Clash)
    # Detect by keys or extension if provided
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
            import json

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
            # If not obviously YAML structure but .yaml extension,
            # might be just text list. Fallback.
            lines = payload_str.splitlines()
        else:
            return [payload_str], drop_stats

    # 4. OpenVPN
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
            decoded = payload_str

        if decoded != payload_str:
            lines = decoded.splitlines()
        else:
            lines = payload_str.splitlines()

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

    # Heuristic for default protocol based on source URL
    default_scheme = "http://"
    if source_url:
        u_lower = source_url.lower()
        if "socks5" in u_lower:
            default_scheme = "socks5://"
        elif "socks4" in u_lower:
            default_scheme = "socks4://"
        # else default http

    for line in lines:
        candidate = line.strip()
        if not candidate:
            continue
        if candidate.startswith("#"):
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

                        # Heuristic: "ip:port:user:pass" -> include auth if it looks clean (IPv4 only)
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

                        # Re-validate with new format
                        if not is_plausible_proxy_config(candidate):
                            reason = "implausible_format"
            else:
                reason = "missing_protocol_separator"

        if not reason:
            configs.append(candidate)
        else:
            drop_stats[reason] = drop_stats.get(reason, 0) + 1
            if len(dropped_samples) < 5:
                dropped_samples.append(f"{candidate[:50]}... [{reason}]")

    total_dropped = sum(drop_stats.values())
    if total_dropped > 0:
        total_seen = total_dropped + len(configs)
        drop_rate = (total_dropped / total_seen) if total_seen else 1.0
        log_method = logger.warning if drop_rate > 0.5 else logger.debug
        if len(configs) > 0:
            log_method(
                f"Parsed {len(configs)} configs. Dropped {total_dropped} lines. "
                f"Reasons: {drop_stats}"
            )
        else:
            log_method(
                f"All lines dropped. Reasons: {drop_stats}. Samples: {dropped_samples}"
            )

    return configs, drop_stats
