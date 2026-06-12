# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import json
from typing import List, Optional, Dict, Any
from ..models import Proxy
from .common import Adapter

logger = logging.getLogger(__name__)


class SIP008Adapter(Adapter):
    """Export to SIP008 JSON format."""

    def export(
        self,
        proxies: List[Proxy],
        washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        servers = []
        for p in proxies:
            if p.protocol == "shadowsocks":
                server = {
                    "server": p.address,
                    "server_port": p.port,
                    "password": p.details.get("password", ""),
                    "method": p.details.get("method", "chacha20-ietf-poly1305"),
                    "remarks": p.remarks,
                }
                servers.append(server)

        logger.info(f"SIP008 export summary: {len(servers)} Shadowsocks servers")
        return json.dumps(
            {"version": 1, "servers": servers, "bytes_used": 0, "bytes_remaining": 0},
            indent=2,
        )
