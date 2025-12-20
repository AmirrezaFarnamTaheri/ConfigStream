import json
import logging
from typing import Optional
from ..models import Proxy

logger = logging.getLogger(__name__)


def parse_clash_json(config: str) -> Optional[Proxy]:
    """Parse a single Clash proxy entry serialized as JSON."""
    try:
        data = json.loads(config)
        if not isinstance(data, dict):
            return None

        # Check for mandatory Clash fields
        if "name" not in data or "type" not in data or "server" not in data:
            return None

        # Map to Proxy model
        protocol = data["type"].lower()
        address = data["server"]
        port = int(data.get("port", 0))
        uuid = data.get("uuid") or data.get("password") or ""

        # Basic mapping
        if protocol == "vmess":
            uuid = data.get("uuid", "")
        elif protocol == "vless":
            uuid = data.get("uuid", "")
        elif protocol == "trojan":
            uuid = data.get("password", "")
        elif protocol == "ss" or protocol == "shadowsocks":
            protocol = "shadowsocks"
            uuid = ""  # SS uses password in details
            data["password"] = data.get("password", "")
            data["method"] = data.get("cipher", "")

        return Proxy(
            config=config,  # Store the JSON blob as config
            protocol=protocol,
            address=address,
            port=port,
            uuid=uuid,
            details=data,
            remarks=data.get("name", ""),
        )
    except Exception as e:
        logger.debug(f"Failed to parse Clash JSON: {e}")
        return None
