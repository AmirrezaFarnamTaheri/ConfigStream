import logging
from typing import List, Tuple, Dict, Any

from .decoders import safe_b64_decode
from ..constants import (
    MAX_CONFIG_LINE_LENGTH,
    MAX_LINES_PER_SOURCE,
    VALID_PROTOCOLS,
    MAX_B64_OUTPUT_SIZE,
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
    if len(protocol) > 20 or len(rest) < 4:
        return False

    # [FIX] Relax noise check
    special_char_count = sum(
        1 for c in rest if not c.isalnum() and c not in ":-_./@#%?&=+,;()~[]"
    )
    if special_char_count > len(rest) * 0.7:
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
    payload: Any, max_lines: int = MAX_LINES_PER_SOURCE
) -> Tuple[List[str], Dict[str, int]]:
    """
    Extract configuration lines with validation and limits.

    Returns:
        Tuple[List[str], Dict[str, int]]: A tuple containing the list of valid config lines
        and a dictionary of drop reasons (count by reason).
    """
    drop_stats: Dict[str, int] = {}

    # [FIX] CRITICAL: Pre-check size to prevent OOM on massive files
    # Limit to 50MB (plenty for any legitimate config list)
    if hasattr(payload, "__len__") and len(payload) > 50 * 1024 * 1024:
        logger.warning(
            "extract_config_lines: Payload exceeds 50MB limit. Dropping to prevent OOM."
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
                logger.debug("extract_config_lines: Failed to decode binary payload.")
                return [], {"decode_error": 1}
    elif isinstance(payload, str):
        payload_str = payload
    else:
        logger.debug(f"extract_config_lines: Invalid payload type {type(payload)}.")
        return [], {"invalid_type": 1}

    if not payload_str.strip():
        return [], {"empty_payload": 1}

    # [FIX] Check for Clash/YAML or V2Ray JSON
    if payload_str.strip().startswith("{"):
        return [payload_str], {}

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
        if (
            not candidate
            or candidate.startswith("#")
            or len(candidate) > MAX_CONFIG_LINE_LENGTH
        ):
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
            # Lines without '://' are dropped unless it's a known format handled elsewhere
            # But here we expect URIs
            reason = "missing_protocol_separator"

        if not reason:
            configs.append(candidate)
        else:
            drop_stats[reason] = drop_stats.get(reason, 0) + 1
            if len(dropped_samples) < 5:
                dropped_samples.append(f"{candidate[:50]}... [{reason}]")

    total_dropped = sum(drop_stats.values())
    if total_dropped > 0:
        if len(configs) > 0:
            logger.info(
                f"Parsed {len(configs)} configs. Dropped {total_dropped} lines. "
                f"Reasons: {drop_stats}"
            )
        else:
            logger.debug(
                f"All lines dropped. Reasons: {drop_stats}. Samples: {dropped_samples}"
            )

    return configs, drop_stats
