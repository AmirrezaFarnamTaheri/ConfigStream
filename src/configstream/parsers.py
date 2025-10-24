import base64
import binascii
import json
import logging
from typing import Optional, List
from urllib.parse import parse_qs, unquote, urlparse

from .models import Proxy

from .constants import (
    MAX_B64_INPUT_SIZE,
    MAX_B64_OUTPUT_SIZE,
    MAX_CONFIG_LINE_LENGTH,
    MAX_LINES_PER_SOURCE,
    VALID_PROTOCOLS,
)

logger = logging.getLogger(__name__)

VALID_B64_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r \t")


def _validate_b64_input(data: str) -> Optional[str]:
    """Validate base64 string before attempting decode."""
    if not isinstance(data, str):
        logger.warning(f"Expected string, got {type(data).__name__}")
        return None

    trimmed = data.strip()
    if not trimmed:
        logger.debug("Empty base64 input")
        return None

    if len(trimmed) > MAX_B64_INPUT_SIZE:
        logger.error(f"Base64 input too large: {len(trimmed)} bytes (max: {MAX_B64_INPUT_SIZE})")
        return None

    invalid_chars = set(trimmed) - VALID_B64_CHARS
    if invalid_chars:
        logger.warning(f"Invalid base64 characters: {invalid_chars}")
        return None

    cleaned = "".join(c for c in trimmed if c not in " \n\r\t")
    padding_needed = (4 - len(cleaned) % 4) % 4
    if padding_needed > 0:
        cleaned += "=" * padding_needed

    return cleaned


def _safe_b64_decode(data: str) -> str:
    """Safely decode base64 with comprehensive validation."""
    validated = _validate_b64_input(data)
    if validated is None:
        return data

    try:
        decoded_bytes = base64.b64decode(validated, validate=True)

        if len(decoded_bytes) > MAX_B64_OUTPUT_SIZE:
            logger.error(
                f"Decoded output too large: {len(decoded_bytes)} bytes (max: {MAX_B64_OUTPUT_SIZE})"
            )
            return data

        try:
            return decoded_bytes.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning("Decoded data is not valid UTF-8")
            return data
    except (binascii.Error, ValueError) as exc:
        logger.warning(f"Base64 decode failed: {exc}")
        return data
    except MemoryError:
        logger.error("Out of memory decoding base64")
        return data
    except Exception as exc:
        logger.error(f"Unexpected error decoding base64: {exc}")
        return data


def _is_plausible_proxy_config(config: str) -> bool:
    """Basic plausibility check for proxy configuration."""
    if "://" not in config:
        return False
    protocol, rest = config.split("://", 1)
    if len(protocol) > 20 or len(rest) < 5:
        return False
    special_char_count = sum(1 for c in rest if not c.isalnum() and c not in ":-_./@#%?&=")
    if special_char_count > len(rest) * 0.5:
        return False
    return True


def _extract_config_lines(payload: str, max_lines: int = MAX_LINES_PER_SOURCE) -> List[str]:
    """Extract configuration lines with validation and limits."""
    if not isinstance(payload, str) or not payload.strip():
        return []

    lines = payload.splitlines()
    if len(lines) > max_lines:
        logger.warning(f"Payload has {len(lines)} lines, truncating to {max_lines}")
        lines = lines[:max_lines]

    valid_protocols_tuple = tuple(f"{p}://" for p in VALID_PROTOCOLS)

    configs = []
    for i, line in enumerate(lines, 1):
        candidate = line.strip()
        if not candidate or candidate.startswith("#") or len(candidate) > MAX_CONFIG_LINE_LENGTH:
            continue
        if candidate.startswith(valid_protocols_tuple) and _is_plausible_proxy_config(candidate):
            configs.append(candidate)
    return configs


def _parse_vmess(config: str) -> Optional[Proxy]:
    try:
        if not config.startswith("vmess://"):
            return None
        data = config[len("vmess://") :]
        if len(data) > 10000:
            logger.warning(f"VMess config too long: {len(data)} bytes")
            return None
        vmess_data = json.loads(base64.b64decode(data).decode("utf-8"))

        if not all(k in vmess_data for k in ["add", "port", "id"]):
            return None
        port = int(vmess_data["port"])
        if not (1 <= port <= 65535):
            return None
        address = vmess_data["add"]
        if not address or len(address) > 255:
            return None
        uuid = vmess_data["id"]
        if not uuid or len(uuid) > 100:
            return None

        return Proxy(
            config=config,
            protocol="vmess",
            address=address,
            port=port,
            uuid=uuid,
            remarks=vmess_data.get("ps", "")[:200],
            details=vmess_data,
        )
    except (json.JSONDecodeError, binascii.Error, KeyError, ValueError) as e:
        logger.debug(f"Failed to parse VMess: {str(e)[:100]}")
        return None


def _parse_vless(config: str) -> Optional[Proxy]:
    try:
        parsed = urlparse(config)
        if not parsed.hostname or len(parsed.hostname) > 255:
            return None
        port = parsed.port or 443
        if not (1 <= port <= 65535):
            return None
        uuid = parsed.username or ""
        if not uuid or len(uuid) > 100:
            return None

        return Proxy(
            config=config,
            protocol="vless",
            address=parsed.hostname,
            port=port,
            uuid=uuid,
            remarks=unquote(parsed.fragment or "")[:200],
            details={k: v[0] for k, v in parse_qs(parsed.query).items()},
        )
    except (ValueError, IndexError) as e:
        logger.debug(f"Failed to parse VLESS: {e}")
        return None


def _parse_ss(config: str) -> Optional[Proxy]:
    try:
        if "@" not in config:
            return None
        encoded_part, host_part = config.replace("ss://", "").split("@", 1)
        if len(encoded_part) > 1000:
            return None  # Limit on encoded part

        decoded_info = _safe_b64_decode(encoded_part)
        if not decoded_info or ":" not in decoded_info:
            return None
        method, password = decoded_info.split(":", 1)

        host, port_remark = host_part.split(":", 1)
        if len(host) > 255:
            return None
        port_str, remark = port_remark.split("#", 1) if "#" in port_remark else (port_remark, "")
        port = int(port_str)
        if not (1 <= port <= 65535):
            return None

        return Proxy(
            config=config,
            protocol="shadowsocks",
            address=host,
            port=port,
            remarks=unquote(remark or "")[:200],
            details={"method": method, "password": password},
        )
    except (ValueError, IndexError, binascii.Error) as e:
        logger.debug(f"Failed to parse Shadowsocks: {e}")
        return None


def _parse_trojan(config: str) -> Optional[Proxy]:
    try:
        parsed = urlparse(config)
        if not parsed.hostname or len(parsed.hostname) > 255:
            return None
        port = parsed.port or 443
        if not (1 <= port <= 65535):
            return None
        uuid = parsed.username or ""
        # Trojan passwords can be empty

        return Proxy(
            config=config,
            protocol="trojan",
            address=parsed.hostname,
            port=port,
            uuid=uuid,
            remarks=unquote(parsed.fragment or "")[:200],
            details=parse_qs(parsed.query),
        )
    except (ValueError, IndexError) as e:
        logger.debug(f"Failed to parse Trojan: {e}")
        return None


def _parse_ssr(config: str) -> Optional[Proxy]:
    try:
        if not config.startswith("ssr://"):
            return None
        encoded = config[len("ssr://") :]
        if len(encoded) > 4096:
            return None

        decoded = _safe_b64_decode(encoded)
        if not decoded:
            return None

        parts = decoded.split(":", 5)
        if len(parts) < 6:
            return None

        server, port_str, protocol, cipher, obfs, tail = parts
        if len(server) > 255:
            return None
        port = int(port_str)
        if not (1 <= port <= 65535):
            return None

        password_part, _, param_str = tail.partition("/?")
        password = _safe_b64_decode(password_part)

        params = parse_qs(param_str)
        params_decoded = {}
        for k, v in params.items():
            if v:
                val = v[0]
                decoded_val = _safe_b64_decode(val)
                # If decoding fails, _safe_b64_decode returns the original string.
                # We check if the original string was valid b64 to detect failure.
                if decoded_val == val and _validate_b64_input(val) is None:
                    logger.debug(f"Invalid base64 in SSR param '{k}': {val}")
                    return None
                params_decoded[k] = decoded_val

        return Proxy(
            config=config,
            protocol="ssr",
            address=server,
            port=port,
            remarks=params_decoded.get("remarks", "")[:200],
            details={
                "protocol": protocol,
                "cipher": cipher,
                "obfs": obfs,
                "password": password,
                "params": params_decoded,
            },
        )
    except (ValueError, IndexError) as e:
        logger.debug(f"Failed to parse SSR: {e}")
        return None


def _parse_generic(config: str) -> Proxy | None:
    try:
        parsed = urlparse(config)
        if not parsed.hostname:
            return None
        return Proxy(
            config=config,
            protocol=parsed.scheme,
            address=parsed.hostname,
            port=parsed.port or 80,
            uuid=parsed.username or "",
            details={"password": parsed.password or ""},
            remarks=unquote(parsed.fragment or ""),
        )
    except (ValueError, IndexError) as e:
        logger.debug(f"Failed to parse Generic config: {str(e)[:50]}")
        return None


def _parse_naive(config: str) -> Proxy | None:
    try:
        parsed = urlparse(config.replace("naive+", ""))
        if not parsed.hostname:
            return None
        if not parsed.username or not parsed.password:
            return None
        return Proxy(
            config=config,
            protocol="naive",
            address=parsed.hostname,
            port=parsed.port or 443,
            uuid=parsed.username or "",
            details={"password": parsed.password or ""},
            remarks=unquote(parsed.fragment or ""),
        )
    except (ValueError, IndexError) as e:
        logger.debug(f"Failed to parse Naive config: {str(e)[:50]}")
        return None


def _parse_v2ray_json(config: str) -> Proxy | None:
    stripped = config.strip()
    if not stripped.startswith("{"):
        return None
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return None

    outbound = data.get("outbound")
    outbounds = data.get("outbounds")
    if not outbound and isinstance(outbounds, list) and outbounds:
        outbound = outbounds[0]
    if not outbound:
        return None

    protocol = outbound.get("protocol", "v2ray")
    settings = outbound.get("settings", {})
    server_info = None
    for key in ("vnext", "servers"):
        nodes = settings.get(key)
        if isinstance(nodes, list) and nodes:
            server_info = nodes[0]
            break

    if not server_info:
        return None

    address = server_info.get("address") or server_info.get("server") or server_info.get("ip")
    port = server_info.get("port")
    if not address or port is None:
        return None

    users = server_info.get("users")
    uuid = ""
    if isinstance(users, list) and users:
        uuid = users[0].get("id", "")

    metadata = {
        "protocol": protocol,
        "settings": settings,
    }
    remarks = outbound.get("tag", data.get("remark", ""))

    return Proxy(
        config=config,
        protocol="v2ray",
        address=address,
        port=int(port),
        uuid=uuid,
        remarks=remarks or "",
        details=metadata,
    )


# Generic parser for URL-based schemes
def _parse_url_scheme(config: str, protocol: str, default_port: int) -> Optional[Proxy]:
    try:
        parsed = urlparse(config)
        if not parsed.hostname or len(parsed.hostname) > 255:
            return None
        port = parsed.port or default_port
        if not (1 <= port <= 65535):
            return None

        return Proxy(
            config=config,
            protocol=protocol,
            address=parsed.hostname,
            port=port,
            uuid=parsed.username or "",
            remarks=unquote(parsed.fragment or "")[:200],
            details=parse_qs(parsed.query),
        )
    except (ValueError, IndexError) as e:
        logger.debug(f"Failed to parse {protocol.upper()}: {e}")
        return None


def _parse_hysteria(c: str) -> Optional[Proxy]:
    return _parse_url_scheme(c, "hysteria", 443)


def _parse_hysteria2(c: str) -> Optional[Proxy]:
    proxy = _parse_url_scheme(c, "hysteria2", 443)
    if proxy and not proxy.uuid:
        logger.debug("Hysteria2 config missing password.")
        return None
    return proxy


def _parse_tuic(c: str) -> Optional[Proxy]:
    return _parse_url_scheme(c, "tuic", 443)


def _parse_wireguard(c: str) -> Optional[Proxy]:
    proxy = _parse_url_scheme(c, "wireguard", 51820)
    if not proxy:
        return None
    if (
        not proxy.details
        or "private_key" not in proxy.details
        or not proxy.details.get("private_key")
    ):
        logger.debug("WireGuard config missing private_key.")
        return None
    return proxy


def _parse_xray(c: str) -> Optional[Proxy]:
    proxy = _parse_url_scheme(c, "xray", 443)
    if not proxy or not proxy.uuid:
        logger.debug("XRay config missing UUID.")
        return None
    return proxy


def _parse_snell(c: str) -> Optional[Proxy]:
    """Parse Snell proxy configuration."""
    return _parse_url_scheme(c, "snell", 443)


def _parse_brook(c: str) -> Optional[Proxy]:
    """Parse Brook proxy configuration."""
    return _parse_url_scheme(c, "brook", 9999)


def _parse_juicity(c: str) -> Optional[Proxy]:
    """Parse Juicity proxy configuration."""
    proxy = _parse_url_scheme(c, "juicity", 443)
    if proxy and not proxy.uuid:
        logger.debug("Juicity config missing UUID.")
        return None
    return proxy
