import logging
import re
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse
from ..models import Proxy
from .base import normalize_proxy_details

logger = logging.getLogger(__name__)


def parse_vless(config: str) -> Optional[Proxy]:
    try:
        # [FIX] Aggressive pre-cleaning
        config = config.strip()
        parsed = urlparse(config)
        if not parsed.hostname or len(parsed.hostname) > 255:
            return None
        port = parsed.port or 443
        if not (1 <= port <= 65535):
            return None
        uuid = parsed.username or ""
        if not uuid or len(uuid) > 100:
            return None

        # [FIX] Aggressive sanitization
        raw_details = parse_qs(parsed.query)
        details = {}
        for k, v in raw_details.items():
            # Strip whitespace and non-printable chars from keys and values
            clean_key = k.strip()
            # Values are lists in parse_qs
            clean_val = "".join(c for c in v[0] if c.isprintable()).strip()
            details[clean_key] = clean_val

        # REALITY Verification
        if details.get("security") == "reality":
            if not details.get("pbk"):
                # logger.debug("VLESS Reality missing 'pbk'")
                return None

            sid = details.get("sid", "")
            # [FIX] Validate HEX for sid
            try:
                if sid:
                    int(sid, 16)
                    # Remove any non-hex characters just in case, though int() check handles validity
                    sid = re.sub(r"[^0-9a-fA-F]", "", sid)
                    details["sid"] = sid
            except ValueError:
                logger.debug(f"Invalid non-hex SID: {sid}")
                return None

            if not sid and not details.get("sid"):
                # if sid was invalid or empty originally
                pass

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
