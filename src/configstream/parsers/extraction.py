# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import re
from typing import List, Tuple, Dict, Any

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
            return False

    if "://" not in config:
        return False
    protocol, rest = config.split("://", 1)
    if not protocol or len(protocol) > 20 or len(rest) < 4:
        return False

    # Relax noise check (allowed up to 85% special chars for base64 heavy VLESS)
    # Modern protocols like VLESS/Trojan with huge Base64 payloads can look very "noisy"
    # We increase tolerance to nearly 100% or just check against truly invalid control chars
    # instead of ratio. But keeping a loose ratio check prevents binary garbage.
    # Expanded allowed chars to include more URI safe chars.
    special_char_count = sum(
        1 for c in rest if not c.isalnum() and c not in ":-_./@#%?&=+,;()~[]!*'|$"
    )

    # [FIX] Increased threshold to 0.98 to allow almost fully encrypted strings
    # Some Base64 strings + parameters can be very dense in special chars.
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
    payload: Any, max_lines: int = MAX_LINES_PER_SOURCE, source_url: str = ""
) -> Tuple[List[str], Dict[str, int]]:
    """
    Extract configuration lines with validation and limits.

    Returns:
        Tuple[List[str], Dict[str, int]]: A tuple containing the list of valid config lines
        and a dictionary of drop reasons (count by reason).
    """
    drop_stats: Dict[str, int] = {}

    # CRITICAL: Pre-check size to prevent OOM on massive files
    # Limit to MAX_B64_INPUT_SIZE (Using constant from settings/constants)
    if hasattr(payload, "__len__") and len(payload) > MAX_B64_INPUT_SIZE:
        logger.warning(
            f"extract_config_lines: Payload exceeds {MAX_B64_INPUT_SIZE} bytes limit. Dropping to prevent OOM."
        )
        return [], {"size_limit_exceeded": 1}

    # Handle input type (bytes or str)
    if isinstance(payload, bytes):
        try:
            # Fallback strategy: utf-8 -> latin-1 (covers most cases)
            payload_str = payload.decode("utf-8")
        except UnicodeDecodeError:
            try:
                payload_str = payload.decode("latin-1")
            except Exception:
                # Last resort: ignore errors to salvage printable chars
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

    # Check for Clash/YAML or V2Ray JSON
    stripped_payload = payload_str.strip()
    if stripped_payload.startswith("{"):
        return [payload_str], {}

    # Check for JSON Array (List of configs)
    if stripped_payload.startswith("["):
        try:
            import json
            data = json.loads(stripped_payload)
            if isinstance(data, list):
                # If it's a list of strings, return them. If list of dicts, dump each.
                extracted = []
                for item in data:
                    if isinstance(item, str):
                        extracted.append(item)
                    elif isinstance(item, dict):
                        extracted.append(json.dumps(item))
                if extracted:
                    return extracted, {}
        except Exception as e:
            logger.debug(f"JSON array parse failed: {e}")
            drop_stats["json_array_parse_error"] = 1

    # Try YAML (Clash)
    if "proxies:" in payload_str and (
        "- name:" in payload_str or "-name:" in payload_str
    ):
        try:
            import yaml  # type: ignore
            import json

            data = yaml.safe_load(payload_str)
            proxies = data.get("proxies", [])
            if isinstance(proxies, list):
                # Convert each proxy dict to a JSON string line
                return [json.dumps(p) for p in proxies if isinstance(p, dict)], {}
        except ImportError:
            logger.warning("PyYAML not installed, skipping Clash YAML parsing")
            drop_stats["missing_dependency_yaml"] = 1
        except Exception as e:
            logger.debug(f"Failed to parse Clash YAML: {e}")
            drop_stats["yaml_parse_error"] = 1
        # Fallback to plain text
        return [payload_str], drop_stats

    # Check if it's an OpenVPN file
    if "client" in payload_str and (
        "dev tun" in payload_str or "dev tap" in payload_str
    ):
        if len(payload_str) < MAX_B64_OUTPUT_SIZE:
            return [payload_str], {}
        else:
            logger.warning(
                "extract_config_lines: OpenVPN config exceeds size limit (%d bytes).",
                len(payload_str),
            )
            return [], {"size_limit_exceeded": 1}

    # Attempt Base64 decode for subscriptions
    # Suppress base64 noise by not logging individual failures inside safe_b64_decode
    # (safe_b64_decode already returns None on failure without noisy logs if handled correctly)
    decoded = safe_b64_decode(payload_str)
    if decoded is None:
        decoded = payload_str

    if decoded != payload_str:
        lines = decoded.splitlines()
    else:
        lines = payload_str.splitlines()

    if len(lines) > max_lines:
        logger.warning(f"Payload has {len(lines)} lines, truncating to {max_lines}.")
        lines = lines[:max_lines]
        drop_stats["truncated_lines"] = len(lines) - max_lines

    valid_prefixes = {p for p in VALID_PROTOCOLS if not p.endswith("://")}
    valid_prefixes.update({p + "://" for p in VALID_PROTOCOLS})

    configs = []
    dropped_samples: List[str] = []

    for line in lines:
        candidate = line.strip()
        # Better comment handling: skip # only at start, allow # in URI fragment
        if not candidate:
            continue
        if candidate.startswith("#"):
            continue

        if len(candidate) > MAX_CONFIG_LINE_LENGTH:
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
            # [FIX] Lines without '://' are dropped, BUT we now check for IP:PORT format
            # Support both IPv4 (strictly validated) and IPv6 (bracketed)

            # IPv4: IP:PORT (e.g. 1.2.3.4:8080)
            ipv4_pattern = r"^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}:\d{1,5}$"

            # IPv6: [IP]:PORT (e.g. [2001:db8::1]:8080)
            # Basic check for brackets and colon-port
            ipv6_pattern = r"^\[[a-fA-F0-9:]+\]:\d{1,5}$"

            if re.match(ipv4_pattern, candidate) or re.match(ipv6_pattern, candidate):
                # Interpret bare IP:port as http proxy
                # We prepend 'http://' to make it a valid URL for parsing
                # Heuristic: If source name implies SOCKS, use socks5://
                scheme = "http://"
                if source_url and ("socks" in source_url.lower()):
                    scheme = "socks5://"

                candidate = scheme + candidate
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
        src_tag = f"[{source_url}] " if source_url else ""
        if len(configs) > 0:
            logger.info(
                f"{src_tag}Parsed {len(configs)} configs. Dropped {total_dropped} lines. "
                f"Reasons: {drop_stats}"
            )
        else:
            logger.debug(
                f"{src_tag}All lines dropped. Reasons: {drop_stats}. Samples: {dropped_samples}"
            )

    return configs, drop_stats
