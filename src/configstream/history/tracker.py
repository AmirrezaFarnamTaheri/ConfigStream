import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone

from ..models import Proxy
from ..quality.storage import QualityStorage

logger = logging.getLogger(__name__)


class ProxyHistoryTracker:
    """
    Manages the persistent history of proxies, including:
    - Availability over time
    - Latency trends
    - Reliability scoring
    """

    def __init__(self, storage: Optional[QualityStorage] = None):
        self.storage = storage or QualityStorage()
        self.session_id = datetime.now(timezone.utc).isoformat()

    def update_history(self, proxies: List[Proxy]):
        """
        Updates the history database with the latest test results.
        """
        if not self.storage:
            logger.warning("History storage not initialized, skipping update.")
            return

        for proxy in proxies:
            self.storage.record_run(
                proxy=proxy,
                latency=proxy.latency,
                is_working=proxy.is_working,
                session_id=self.session_id,
            )

    def get_history(self, proxy_id: str) -> Dict[str, Any]:
        """
        Retrieves the history for a specific proxy.
        """
        return self.storage.get_proxy_history(proxy_id)

    def close(self):
        """
        Closes the underlying storage connection.
        """
        if self.storage:
            self.storage.close()
