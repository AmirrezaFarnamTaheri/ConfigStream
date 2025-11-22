import logging
import re
from typing import Optional
from ..models import Proxy

logger = logging.getLogger(__name__)


def parse_openvpn(config: str) -> Optional[Proxy]:
    """Parse OpenVPN configuration content."""
    try:
        # Check for basic OVPN markers
        if "client" not in config:
            return None

        # Extract remote
        remotes = re.findall(r"^remote\s+(\S+)\s+(\d+)", config, re.MULTILINE)
        if not remotes:
            # Maybe in <connection> block?
            remotes = re.findall(r"remote\s+(\S+)\s+(\d+)", config)

        if not remotes:
            return None

        # Pick the first remote for now (simplification)
        host, port_str = remotes[0]
        try:
            port = int(port_str)
        except (ValueError, TypeError):
            logger.debug("Invalid port in openvpn config: %s", port_str)
            return None

        # Extract Proto
        proto_match = re.search(r"^proto\s+(\w+)", config, re.MULTILINE)
        transport = proto_match.group(1) if proto_match else "udp"

        return Proxy(
            config=config,  # Store the full file content as config
            protocol="openvpn",
            address=host,
            port=port,
            details={
                "transport": transport,
                # We don't parse keys out; the config is the payload
            },
            remarks="OpenVPN Config",
        )

    except Exception as e:
        logger.debug("Failed to parse OpenVPN: %s", e)
        return None
