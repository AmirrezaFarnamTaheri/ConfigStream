# SPDX-License-Identifier: AGPL-3.0-or-later
import abc
import logging
from typing import List, Optional, Dict, Any
from ..models import Proxy

logger = logging.getLogger(__name__)

def _extract_sni(details: Dict[str, Any]) -> str:
    for key in (
        "sni",
        "server_name",
        "original_host",
        "host",
        "http_host",
        "ws_host",
    ):
        value = details.get(key)
        if value:
            return str(value)
    return ""

class Adapter(abc.ABC):
    """Base class for proxy adapters."""

    @abc.abstractmethod
    def export(
        self,
        proxies: List[Proxy],
        washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Export a list of proxies to the adapter's format."""
