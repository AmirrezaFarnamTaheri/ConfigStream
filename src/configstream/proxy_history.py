import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, cast
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from .models import Proxy

logger = logging.getLogger(__name__)


class ProxyHistoryTracker:
    """Tracks historical performance data for proxies."""

    def __init__(
        self, history_path: Path = Path("data/proxy_history.json"), max_entries: int = 100
    ):
        """
        Initialize history tracker.

        Args:
            history_path: Path to store history data
            max_entries: Maximum number of historical entries to keep per proxy
        """
        self.history_path = Path(history_path)
        self.max_entries = max_entries
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_data = self._load_history()
        self._dirty = False  # Track if we have unsaved changes

    def _load_history(self) -> Dict[str, Any]:
        """Load history data from disk."""
        if self.history_path.exists():
            try:
                data: Dict[str, Any] = json.loads(self.history_path.read_text())
                return data
            except Exception as e:
                logger.warning("Failed to load proxy history: %s", e)
        return {}

    def _save_history(self) -> None:
        """Save history data to disk."""
        try:
            self.history_path.write_text(json.dumps(self.history_data, indent=2))
            self._dirty = False
        except Exception as e:
            logger.error("Failed to save proxy history: %s", e)

    def flush(self) -> None:
        """Public method to force write history to disk if changes exist."""
        if self._dirty:
            logger.info("Flushing proxy history to disk...")
            self._save_history()

    def record_test_result(self, proxy: Proxy) -> None:
        """
        Record a test result for a proxy.
        Note: Does NOT write to disk immediately. Call flush() at end of pipeline.
        """
        # Use config as unique identifier
        proxy_id = proxy.config

        if proxy_id not in self.history_data:
            self.history_data[proxy_id] = {
                "protocol": proxy.protocol,
                "address": proxy.address,
                "port": proxy.port,
                "entries": [],
            }

        # Create entry
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "is_working": proxy.is_working,
            "latency": proxy.latency,
            "country": proxy.country,
        }

        # Add entry and trim if needed
        self.history_data[proxy_id]["entries"].append(entry)
        if len(self.history_data[proxy_id]["entries"]) > self.max_entries:
            self.history_data[proxy_id]["entries"] = self.history_data[proxy_id]["entries"][
                -self.max_entries :
            ]

        self._dirty = True
        # REMOVED: self._save_history() - causing I/O bottleneck
