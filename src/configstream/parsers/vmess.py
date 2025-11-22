import json
import logging
import base64
import binascii
from typing import Optional
from ..models import Proxy
from ..constants import MAX_CONFIG_LINE_LENGTH
from .base import normalize_proxy_details

logger = logging.getLogger(__name__)


def parse_vmess(config: str) -> Optional[Proxy]:
    try:
        if not config.startswith("vmess://"):
            return None
        data = config[len("vmess://") :]
        if len(data) > 10000:
            logger.warning("VMess config too long: %s bytes", len(data))
            return None
        # Decode and check size before JSON parsing (security: prevent memory bomb)
        decoded = base64.b64decode(data).decode("utf-8")
        if len(decoded) > MAX_CONFIG_LINE_LENGTH:
            logger.warning("VMess decoded data too large: %s bytes", len(decoded))
            return None
        vmess_data = json.loads(decoded)

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

        proxy = Proxy(
            config=config,
            protocol="vmess",
            address=address,
            port=port,
            uuid=uuid,
            remarks=vmess_data.get("ps", "")[:200],
            details=vmess_data,
        )
        normalize_proxy_details(proxy)
        return proxy
    except (json.JSONDecodeError, binascii.Error, KeyError, ValueError) as e:
        logger.debug("Failed to parse VMess: %s", str(e)[:100])
        return None
