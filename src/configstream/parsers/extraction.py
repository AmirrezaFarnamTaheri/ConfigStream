import logging
from typing import List

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
        # It's likely an OVPN file content, which is handled separately
        return True

    # Filter subscription URLs (not proxy configs)
    config_lower = config.lower()
    if config_lower.startswith("https://") or config_lower.startswith("http://"):
        if "@" not in config and any(d in config_lower for d in BLOCKED_DOMAINS):
            # Only treat as subscription if it DOESN'T have user info (no @)
            return False

    if "://" not in config:
        # logger.debug(f"Plausibility check failed: No protocol separator '://' in {config[:50]}...")
        return False
    protocol, rest = config.split("://", 1)
    if len(protocol) > 20 or len(rest) < 4:
        # logger.debug(f"Plausibility check failed: Invalid length for protocol or rest in {config[:50]}...")
        return False

    # [FIX] Relax noise check
    # Some URLs (especially complex VLESS/VMess with long query params) can have many special chars.
    # We increase threshold to 70% and allow more special chars.
    special_char_count = sum(
        1 for c in rest if not c.isalnum() and c not in ":-_./@#%?&=+,;()~"
    )
    if special_char_count > len(rest) * 0.7:
        # logger.debug(f"Plausibility check failed: High noise ratio in {config[:50]}...")
        return False
    return True


def extract_config_lines(
    payload: str, max_lines: int = MAX_LINES_PER_SOURCE
) -> List[str]:
    """Extract configuration lines with validation and limits."""
    if not isinstance(payload, str) or not payload.strip():
        logger.debug("extract_config_lines: Empty or invalid payload type.")
        return []

    # [FIX] Check for Clash/YAML or V2Ray JSON
    # If detected, we return the payload as a single "line" to be parsed by auto_detect
    # which needs to support parsing the full blob.

    # Try JSON (V2Ray JSON)
    if payload.strip().startswith("{"):
        return [payload]

    # Try YAML (Clash) - Look for structural markers
    if "proxies:" in payload and ("- name:" in payload or "-name:" in payload):
        try:
            # Type ignore for optional dependency
            import yaml  # type: ignore
            import json

            data = yaml.safe_load(payload)
            proxies = data.get("proxies", [])
            if isinstance(proxies, list):
                # Convert each proxy dict to a JSON string line
                return [json.dumps(p) for p in proxies if isinstance(p, dict)]
        except ImportError:
            # Warn only once to avoid log spam? Or just debug since it's optional.
            # Using debug as it is an optional dependency.
            logger.debug("PyYAML not installed, skipping Clash YAML parsing")
        except Exception as e:
            logger.debug(f"Failed to parse Clash YAML: {e}")
        # If parsing fails or yields no proxies, return payload for other parsers (fallback)
        return [payload]

    # Check if it's an OpenVPN file
    if "client" in payload and ("dev tun" in payload or "dev tap" in payload):
        logger.debug("extract_config_lines: Detected OpenVPN configuration.")
        # Treat the whole payload as one config
        if len(payload) < MAX_B64_OUTPUT_SIZE:  # Size limit check
            return [payload]
        else:
            logger.warning(
                "extract_config_lines: OpenVPN config exceeds size limit (%d bytes).",
                len(payload),
            )

    # Attempt Base64 decode for subscriptions
    decoded = safe_b64_decode(payload)
    if decoded is None:
        # It's likely not base64, so treat it as plain text (legacy behavior)
        # OR it was invalid base64.
        # However, safe_b64_decode returns None ONLY if it failed validation/decoding but was potentially base64
        # OR if it was just plain text that failed validation as base64.

        # If safe_b64_decode returns None, it means "this is not valid base64 content we should decode".
        # So we fall back to using the original payload as plain text lines.
        decoded = payload

    if decoded != payload:
        logger.debug("Successfully decoded Base64 subscription payload")
        lines = decoded.splitlines()
    else:
        lines = payload.splitlines()

    logger.debug(
        f"Extracting configs from payload of {len(payload)} bytes ({len(lines)} lines)"
    )

    if len(lines) > max_lines:
        logger.warning(
            f"Payload has {len(lines)} lines, truncating to {max_lines}. "
            f"Consider splitting this source or increasing MAX_LINES to avoid data loss."
        )
        lines = lines[:max_lines]

    valid_prefixes = {p for p in VALID_PROTOCOLS if not p.endswith("://")}
    valid_prefixes.update({p + "://" for p in VALID_PROTOCOLS})

    configs = []
    dropped_count = 0
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
        if len(parts) == 2:
            protocol = parts[0]
            reason = ""
            if protocol not in valid_prefixes:
                reason = f"Invalid protocol '{protocol}'"
            elif not is_plausible_proxy_config(candidate):
                reason = "Implausible format or blocked domain"

            if not reason:
                configs.append(candidate)
            else:
                dropped_count += 1
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "Dropping invalid config line: %s... (Reason: %s)",
                        candidate[:100],
                        reason,
                    )
                # [FIX] Keep more samples (20) and log them all if dropped count is high
                if len(dropped_samples) < 20:
                    dropped_samples.append(f"{candidate[:100]} [{reason}]")

    if dropped_count > 0:
        if len(configs) > 0:
            logger.info(
                f"Parsed {len(configs)} valid configs (dropped {dropped_count} lines). "
                f"Success rate: {len(configs)/(len(configs)+dropped_count):.1%}"
            )
        else:
            logger.warning(
                f"All {dropped_count} lines were dropped as invalid/implausible. "
                "Check source format or content."
            )

        if dropped_samples:
            # Enhanced debug logging
            # Log all captured samples
            sample_text = "; ".join(dropped_samples)
            logger.debug(
                f"Dropped lines analysis: Total={dropped_count}. Samples: {sample_text}"
            )
    else:
        logger.info(f"Successfully extracted {len(configs)} configs (0 dropped).")

    return configs
