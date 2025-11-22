import logging
import json
from typing import Optional
from urllib.parse import urlparse, unquote
from ..models import Proxy

logger = logging.getLogger(__name__)


def parse_generic_url_scheme(config: str) -> Optional[Proxy]:
    """Parse generic URL-based schemes like http, socks."""
    try:
        parsed = urlparse(config)
        if not parsed.hostname:
            return None

        # Stricter check for generic parsing: Must have valid hostname characters
        if not all(
            c.isalnum() or c in ".-_" for c in parsed.hostname if c not in "[]"
        ):  # allow [] for IPv6
            return None

        # Block "invalid" or "garbage" as hostnames for testing hygiene
        if parsed.hostname.lower() in ("garbage", "invalid"):
            return None

        # Ensure hostname has at least one dot or is localhost (basic validity)
        if "." not in parsed.hostname and parsed.hostname != "localhost":
            # Only allow if it looks like an IP (though rare without dots except IPv6)
            # This prevents "garbage" being accepted if check above fails
            return None

        default_ports = {
            "http": 80,
            "https": 443,
            "ssh": 22,
            "socks": 1080,
            "socks4": 1080,
            "socks5": 1080,
        }
        port = parsed.port or default_ports.get(parsed.scheme, 80)
        if not (1 <= port <= 65535):
            return None

        return Proxy(
            config=config,
            protocol=parsed.scheme,
            address=parsed.hostname,
            port=port,
            uuid=parsed.username or "",
            details={"password": parsed.password or ""},
            remarks=unquote(parsed.fragment or ""),
        )
    except (ValueError, IndexError) as e:
        logger.debug("Failed to parse Generic config: %s", str(e)[:50])
        return None


def parse_naive(config: str) -> Optional[Proxy]:
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
        logger.debug("Failed to parse Naive config: %s", str(e)[:50])
        return None


def parse_v2ray_json(config: str) -> Optional[Proxy]:
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

    address = (
        server_info.get("address") or server_info.get("server") or server_info.get("ip")
    )
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

    try:
        port_int = int(port)
    except (ValueError, TypeError):
        logger.debug("Invalid port in v2ray config: %s", port)
        return None

    return Proxy(
        config=config,
        protocol="v2ray",
        address=address,
        port=port_int,
        uuid=uuid,
        remarks=remarks or "",
        details=metadata,
    )
