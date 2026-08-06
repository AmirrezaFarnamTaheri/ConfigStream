# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import logging
import binascii
from typing import Optional
from ..models import Proxy
from ..constants import MAX_CONFIG_LINE_LENGTH
from .base import normalize_proxy_details, safe_b64_decode
from ..security_validator import safe_log_text

logger = logging.getLogger(__name__)


def parse_vmess(config: str) -> Optional[Proxy]:
    try:
        if not config.startswith("vmess://"):
            return None
        data = config[len("vmess://") :]

        # Use safe_b64_decode to handle URL-encoding and padding automatically
        decoded = safe_b64_decode(data)
        if decoded is None:
            return None

        # safe_b64_decode returns original data on failure; check if it looks like JSON
        if not decoded.strip().startswith("{"):
            return None

        if MAX_CONFIG_LINE_LENGTH > 0 and len(decoded) > MAX_CONFIG_LINE_LENGTH:
            logger.warning("VMess decoded data too large: %d bytes", len(decoded))
            return None

        vmess_data = json.loads(decoded)

        if not all(k in vmess_data for k in ["add", "port", "id"]):
            return None

        try:
            port = int(vmess_data["port"])
        except (ValueError, TypeError):
            return None

        if not (1 <= port <= 65535):
            return None

        address = vmess_data["add"]
        if not address or len(str(address)) > 255:
            return None

        uuid = vmess_data["id"]
        # Basic UUID length check (standard is 36, but some implementations use different IDs)
        if not uuid or len(str(uuid)) > 100:
            return None

        # Respect AlterID if provided, otherwise default to 0 (AEAD mode)
        if "aid" in vmess_data:
            try:
                vmess_data["aid"] = int(vmess_data["aid"])
            except (ValueError, TypeError):
                vmess_data["aid"] = 0
        else:
            vmess_data["aid"] = 0

        ps = vmess_data.get("ps", "")
        if isinstance(ps, str):
            ps = ps[:200]
        else:
            ps = str(ps)[:200]

        proxy = Proxy(
            config=config,
            protocol="vmess",
            address=str(address),
            port=port,
            uuid=str(uuid),
            remarks=ps,
            details=vmess_data,
        )
        normalize_proxy_details(proxy)
        return proxy
    except (json.JSONDecodeError, binascii.Error, KeyError, ValueError, TypeError) as e:
        logger.debug("Failed to parse VMess: %s", safe_log_text(str(e)[:100]))
        return None
