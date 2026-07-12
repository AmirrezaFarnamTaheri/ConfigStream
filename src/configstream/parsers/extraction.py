# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import logging
import math
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
from ..security_validator import SecurityValidator

logger = logging.getLogger(__name__)

_IPV4_PORT_PATTERN = re.compile(
    r"\b(?P<host>(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}):(?P<port>\d{1,5})\b"
)
_IPV6_PORT_PATTERN = re.compile(r"\[(?P<host>[0-9A-Fa-f:]+)\]:(?P<port>\d{1,5})")
_OBFUSCATED_IPV4_PORT_PATTERN = re.compile(
    r"\b(?P<host>(?:0x[0-9A-Fa-f]+|0[0-7]+|\d+)(?:\.(?:0x[0-9A-Fa-f]+|0[0-7]+|\d+)){3}):(?P<port>\d{1,5})\b"
)


def _parse_ip_octet(token: str) -> Optional[int]:
    tok = token.strip()
    if not tok:
        return None
    try:
        if tok.lower().startswith("0x"):
            value = int(tok, 16)
        elif len(tok) > 1 and tok.startswith("0"):
            value = int(tok, 8)
        else:
            value = int(tok, 10)
    except ValueError:
        return None
    return value if 0 <= value <= 255 else None


def _decode_obfuscated_ipv4(host: str) -> Optional[str]:
    parts = host.split(".")
    if len(parts) != 4:
        return None
    decoded = []
    for part in parts:
        octet = _parse_ip_octet(part)
        if octet is None:
            return None
        decoded.append(str(octet))
    return ".".join(decoded)


def _shannon_entropy(sample: str) -> float:
    if not sample:
        return 0.0
    counts: Dict[str, int] = {}
    for ch in sample:
        counts[ch] = counts.get(ch, 0) + 1
    length = float(len(sample))
    entropy = 0.0
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


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

    # Protocol-aware noise limits:
    # VLESS links can carry heavily encoded query strings, so allow a higher ratio.
    noise_threshold = 0.50
    proto_lower = protocol.lower()
    if proto_lower in ("vless", "exclave"):
        noise_threshold = 0.65
    elif proto_lower in ("vmess", "trojan"):
        noise_threshold = 0.58
    if len(rest) > 200:
        noise_threshold += 0.05
    if len(rest) > 500:
        noise_threshold += 0.05
    noise_threshold = min(0.90, noise_threshold)

    special_char_count = sum(
        1
        for c in rest
        if not c.isalnum() and c not in ":-_./@#%?&=+,;()~[]!*'|${}<>\\^\""
    )

    if len(rest) > 20 and special_char_count > len(rest) * noise_threshold:
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
            "extract_config_lines: Payload exceeds %d bytes limit. Dropping to prevent OOM.",
            MAX_B64_INPUT_SIZE,
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
        logger.debug(
            "extract_config_lines: Invalid payload type %s.",
            SecurityValidator.sanitize_log_message(str(type(payload))),
        )
        return [], {"invalid_type": 1}

    if not payload_str.strip():
        return [], {"empty_payload": 1}

    # Reject hostile/binary payloads before deeper parsing to avoid OOM spikes.
    if "\x00" in payload_str:
        logger.debug("Dropping payload with NULL bytes.")
        return [], {"hostile_payload": 1}

    sample = payload_str[:8192]
    non_printable = sum(
        1 for c in sample if ord(c) < 9 or (13 < ord(c) < 32) or ord(c) == 127
    )
    if sample:
        non_printable_ratio = non_printable / len(sample)
        if non_printable_ratio > 0.20 and _shannon_entropy(sample) > 7.2:
            logger.debug(
                "Dropping high-entropy binary-like payload (ratio=%.2f).",
                non_printable_ratio,
            )
            return [], {"hostile_payload": 1}

    # HTML Pollution Detection
    # Detect common HTML tags at start of content
    stripped_start = payload_str.strip()[:100].lower()
    if (
        "<!doctype html>" in stripped_start
        or "<html" in stripped_start
        or "<head" in stripped_start
        or "<body" in stripped_start
    ):
        # HTML content detected. Large pure-HTML pages are likely error pages, not configs.
        # Small pages or those containing proxy URIs in <pre> tags are still scanned.
        if len(payload_str) > 100_000 and "://" not in payload_str[:1000]:
            logger.debug(
                "Dropping large HTML payload (%d bytes) with no proxy URIs",
                len(payload_str),
            )
            return [], {"html_page": 1}
        logger.debug("HTML detected but proceeding — may contain embedded configs")

    # 1. Check for JSON Array (e.g. ["vmess://...", ...])
    if payload_str.strip().startswith("["):
        try:
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
            logger.debug(
                "Failed to parse JSON array: %s",
                SecurityValidator.sanitize_log_message(str(e)),
            )
            lines = payload_str.splitlines()

    # 2. Check for V2Ray JSON Object (single)
    elif payload_str.strip().startswith("{"):
        # Check if it's V2Ray (outbounds) or just a JSON object wrapper
        try:
            data = json.loads(payload_str)
            # If it has "proxies" key (Clash/Mihomo JSON)
            if "proxies" in data and isinstance(data["proxies"], list):
                return [
                    json.dumps(p) for p in data["proxies"] if isinstance(p, dict)
                ], {}
            # If standard V2Ray, return as is
            return [payload_str], {}
        except Exception:
            logging.getLogger(__name__).debug("Suppressed broad exception", exc_info=True)
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

            data = yaml.safe_load(payload_str)
            # Handle list of proxies
            proxies = data if isinstance(data, list) else data.get("proxies", [])

            if isinstance(proxies, list):
                return [json.dumps(p) for p in proxies if isinstance(p, dict)], {}
        except ImportError:
            logger.warning("PyYAML not installed, skipping Clash YAML parsing")
            drop_stats["missing_dependency_yaml"] = 1
        except Exception as e:
            logger.debug(
                "Failed to parse Clash YAML: %s",
                SecurityValidator.sanitize_log_message(str(e)),
            )
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
            "Payload has %d lines, truncating to %d.",
            original_count,
            max_lines,
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

    html_drops = 0

    for line in lines:
        candidate = line.strip()
        if not candidate:
            continue
        if candidate.startswith("#"):
            continue

        # Individual HTML Line Detection (Robust)
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
            host_is_obfuscated = False
            match = _IPV6_PORT_PATTERN.search(candidate)
            if not match:
                match = _IPV4_PORT_PATTERN.search(candidate)
            if not match:
                match = _OBFUSCATED_IPV4_PORT_PATTERN.search(candidate)
                host_is_obfuscated = match is not None

            if match:
                host = match.group("host")
                if host_is_obfuscated:
                    decoded = _decode_obfuscated_ipv4(host)
                    if decoded:
                        host = decoded
                    else:
                        reason = "invalid_obfuscated_ip"
                        host = ""
                port_str = match.group("port")
                try:
                    port_val = int(port_str)
                except (TypeError, ValueError):
                    reason = "invalid_port"
                else:
                    if reason:
                        pass
                    elif not (1 <= port_val <= 65535):
                        reason = "invalid_port"
                    else:
                        addr = f"[{host}]" if ":" in host else host
                        candidate = f"{default_scheme}{addr}:{port_val}"

                        # Heuristic: "ip:port:user:pass" -> include auth if it looks clean (IPv4 only)
                        # Also check for "user:pass@ip:port" (SIP002 raw style)
                        if ":" not in host:
                            prefix = match.group(0)  # e.g. 1.2.3.4:80
                            raw_trim = raw_candidate.strip()

                            # Case 1: IP:PORT:USER:PASS (SOCKS/HTTP auth)
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

                            # Case 2: USER:PASS@IP:PORT (Raw SS/SIP002)
                            elif raw_trim.endswith("@" + prefix):
                                head = raw_trim[: -len("@" + prefix)]
                                if ":" in head:
                                    # Might be method:password
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
                                        # Use ss:// scheme if it looks like encryption method
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
                sample = f"[dropped_line] [{reason}]"
                dropped_samples.append(SecurityValidator.sanitize_log_message(sample))

    if html_drops > 0:
        drop_stats["html_content"] = html_drops

    total_dropped = sum(drop_stats.values())
    if total_dropped > 0:
        total_seen = total_dropped + len(configs)
        drop_rate = (total_dropped / total_seen) if total_seen else 1.0
        # If > 90% drops are HTML, just say "Source returned HTML content"
        if html_drops > total_dropped * 0.9:
            safe_source = (
                SecurityValidator.sanitize_log_message(source_url)
                if source_url
                else "unknown"
            )
            logger.debug(
                "Source %s dropped %d lines of HTML content.",
                safe_source,
                html_drops,
            )
        else:
            log_method = logger.warning if drop_rate > 0.5 else logger.debug
            if len(configs) > 0:
                log_method(
                    "Parsed %d configs. Dropped %d lines. Reasons: %s",
                    len(configs),
                    total_dropped,
                    drop_stats,
                )
            else:
                # Demote to DEBUG when all lines are missing protocol separator
                # (binary/garbage content) to prevent log spam from fuzz tests
                all_missing_sep = (
                    drop_stats.get("missing_protocol_separator", 0) == total_dropped
                )
                method = logger.debug if all_missing_sep else log_method
                method(
                    "All lines dropped. Reasons: %s. Samples: %s",
                    drop_stats,
                    dropped_samples,
                )

    return configs, drop_stats
