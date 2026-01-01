# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Storage module for Proxy History.
Handles loading and saving of history data.
"""

import orjson as json
import logging
from pathlib import Path
from typing import Any, Dict

from ..utils import AtomicFileWriter

logger = logging.getLogger(__name__)


class HistoryStorage:
    """Handles persistence of proxy history data."""

    def __init__(self, history_path: Path):
        self.history_path = history_path
        self.history_path.parent.mkdir(parents=True, exist_ok=True)

    def load_history(self) -> Dict[str, Any]:
        """Load history data from disk."""
        if self.history_path.exists():
            try:
                # Security: Check file size before loading to prevent OOM
                file_size = self.history_path.stat().st_size
                MAX_HISTORY_FILE_SIZE = 100 * 1024 * 1024  # 100MB limit
                if file_size > MAX_HISTORY_FILE_SIZE:
                    logger.error(
                        "History file too large: %s bytes (max: %s)",
                        file_size,
                        MAX_HISTORY_FILE_SIZE,
                    )
                    return {}
                data: Dict[str, Any] = json.loads(self.history_path.read_bytes())
                return data
            except Exception as e:
                logger.warning(f"Failed to load proxy history: {e}")
        return {}

    def save_history(self, history_data: Dict[str, Any]) -> None:
        """Save history data to disk."""
        try:
            # Use orjson for faster serialization with indent
            content = json.dumps(history_data, option=json.OPT_INDENT_2).decode()
            AtomicFileWriter.write_text(self.history_path, content)
        except Exception as e:
            logger.error(f"Failed to save proxy history: {e}")
