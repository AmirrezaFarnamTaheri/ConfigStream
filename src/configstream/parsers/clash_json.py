# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import logging
from typing import Optional
from ..models import Proxy
from ..constants import MAX_CONFIG_LINE_LENGTH
from ..security_validator import SecurityValidator
from .base import normalize_proxy_details

logger = logging.getLogger(__name__)


def parse_clash_json(config: str) -> Optional[Proxy]:
    """Parse a single Clash proxy entry serialized as JSON."""
    try:
        config = config.strip()
        # Enforce MAX_CONFIG_LINE_LENGTH
        if MAX_CONFIG_LINE_LENGTH > 0 and len(config) > MAX_CONFIG_LINE_LENGTH:
            return None

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
            password = data.get("password", "")
            if not password:
                # Reject Shadowsocks without password immediately
                return None
            data["password"] = password
            data["method"] = data.get("cipher", "")
        elif protocol == "wireguard" or protocol == "wg":
            protocol = "wireguard"
            # Enforce private_key for WireGuard (accept common aliases)
            if "private_key" not in data:
                if "private-key" in data:
                    data["private_key"] = data.pop("private-key")
                elif "privateKey" in data:
                    data["private_key"] = data.pop("privateKey")
                else:
                    logger.debug(
                        "Dropping WireGuard proxy missing private_key: %s",
                        SecurityValidator.sanitize_log_message(address),
                    )
                    return None

        proxy = Proxy(
            config=config,  # Store the JSON blob as config
            protocol=protocol,
            address=address,
            port=port,
            uuid=uuid,
            details=data,
            remarks=data.get("name", ""),
        )
        normalize_proxy_details(proxy)
        return proxy
    except Exception as e:
        logger.debug(
            "Failed to parse Clash JSON: %s",
            SecurityValidator.sanitize_log_message(str(e)),
        )
        return None
