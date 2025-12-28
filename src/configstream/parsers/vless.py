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

        hostname = parsed.hostname
        if not hostname or len(hostname) > 255:
            return None

        try:
            port = parsed.port or 443
        except ValueError:
            return None

        if not (1 <= port <= 65535):
            return None

        # [FIX] Aggressive sanitization
        raw_details = parse_qs(parsed.query)
        details = {}
        for k, v in raw_details.items():
            # Strip whitespace and non-printable chars from keys and values
            clean_key = k.strip()
            # Values are lists in parse_qs
            # Handle potential None values inside list (though uncommon from parse_qs)
            clean_val = "".join(c for c in v[0] if c.isprintable()).strip()
            details[clean_key] = clean_val

        uuid = parsed.username or ""
        # Fallback: check query params for uuid
        if not uuid:
            uuid = details.get("uuid", "")

        # Strict UUID validation
        if not uuid or len(uuid) > 100:
            return None

        # Valid UUIDv4 is 36 chars. Allow some flexibility for other ID formats,
        # but reject obviously invalid short strings or non-hex strings that look like noise.
        # Standard UUID: 8-4-4-4-12 hex digits
        if len(uuid) < 30 and not re.match(r"^[a-fA-F0-9-]{32,36}$", uuid):
            # If it's short and not a hex string, it's likely a misparsed username
            return None

        # REALITY Verification
        if details.get("security") == "reality":
            if not details.get("pbk"):
                logger.debug("VLESS Reality missing 'pbk'")
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
                # if sid was invalid or empty originally, we allow it (empty sid is valid)
                logger.debug("VLESS Reality with empty SID - allowing")

        # Additional safety check for uuid as remark
        if uuid.lower() in ["vless", "admin", "root"]:
            return None

        proxy = Proxy(
            config=config,
            protocol="vless",
            address=str(hostname),
            port=port,
            uuid=uuid,
            remarks=unquote(parsed.fragment or "")[:200],
            details=details,
        )
        normalize_proxy_details(proxy)
        return proxy
    except (ValueError, IndexError, AttributeError) as e:
        logger.debug(f"Failed to parse VLESS: {e}")
        return None
