import logging
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse
from ..models import Proxy
from .base import normalize_proxy_details

logger = logging.getLogger(__name__)


def parse_trojan(config: str) -> Optional[Proxy]:
    try:
        parsed = urlparse(config)
        # Strict scheme check to prevent false positives in auto-detect
        if parsed.scheme and parsed.scheme.lower() not in ("trojan", "trojan-go"):
            return None

        if not parsed.hostname or len(parsed.hostname) > 255:
            return None
        port = parsed.port or 443
        # port 0 or > 65535 is invalid
        if not (1 <= port <= 65535):
            return None
        uuid = parsed.username or ""
        # Trojan passwords can be empty

        details = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        proxy = Proxy(
            config=config,
            protocol="trojan",
            address=parsed.hostname,
            port=port,
            uuid=uuid,
            remarks=unquote(parsed.fragment or "")[:200],
            details=details,
        )
        normalize_proxy_details(proxy)
        return proxy
    except (ValueError, IndexError) as e:
        logger.debug("Failed to parse Trojan: %s", e)
        return None
