import logging
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse
from ..models import Proxy
from .base import normalize_proxy_details

logger = logging.getLogger(__name__)


def parse_vless(config: str) -> Optional[Proxy]:
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

        details = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        # REALITY Verification
        if details.get("security") == "reality":
            if not details.get("pbk"):
                logger.debug("VLESS Reality missing 'pbk'")
                return None
            if not details.get("sid"):
                logger.debug("VLESS Reality missing 'sid'")
                return None

        proxy = Proxy(
            config=config,
            protocol="vless",
            address=parsed.hostname,
            port=port,
            uuid=uuid,
            remarks=unquote(parsed.fragment or "")[:200],
            details=details,
        )
        normalize_proxy_details(proxy)
        return proxy
    except (ValueError, IndexError) as e:
        logger.debug("Failed to parse VLESS: %s", e)
        return None
