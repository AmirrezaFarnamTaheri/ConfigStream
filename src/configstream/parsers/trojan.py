# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse
from ..models import Proxy
from .base import normalize_proxy_details
from ..constants import MAX_CONFIG_LINE_LENGTH

logger = logging.getLogger(__name__)


def parse_trojan(config: str) -> Optional[Proxy]:
    try:
        config = config.strip()
        if len(config) > MAX_CONFIG_LINE_LENGTH:
            return None

        parsed = urlparse(config)
        # Strict scheme check to prevent false positives in auto-detect
        if parsed.scheme and parsed.scheme.lower() not in ("trojan", "trojan-go"):
            return None

        if not parsed.hostname or len(parsed.hostname) > 255:
            return None
        port = parsed.port or 443
        if not (1 <= port <= 65535):
            return None
        details = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        uuid = parsed.username or ""
        # Fallback: check query params for password
        if not uuid:
            for key in ("password", "pass", "pwd", "token", "uuid", "id"):
                val = details.get(key, "")
                if isinstance(val, str) and val.strip():
                    uuid = val.strip()
                    break

        # Strict Trojan password (stored as username) requirement
        if not uuid:
            return None
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
        logger.debug(f"Failed to parse Trojan: {e}")
        return None
