# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from configstream.security_validator import SecurityValidator
from configstream.utils import _FileLock

EVENT_LOG_FILENAME = "pipeline_events.jsonl"
logger = logging.getLogger(__name__)


class EventStream:
    """
    Handles real-time pipeline event emission.

    Events are sent to the standard logger and persisted as sanitized JSONL so
    artifact bundles can carry lightweight operational evidence without leaking
    URLs, credentials, UUIDs, IP addresses, or long encoded material.
    """

    def __init__(
        self,
        output_dir: Path,
        *,
        persist: bool = True,
        max_message_chars: int = 2000,
    ):
        self.output_dir = Path(output_dir)
        self.persist = persist
        self.max_message_chars = max(256, int(max_message_chars))
        self.event_log_path = self.output_dir / EVENT_LOG_FILENAME

    def _sanitize_message(self, message: Any) -> str:
        safe = SecurityValidator.sanitize_log_message(str(message))
        if len(safe) > self.max_message_chars:
            return f"{safe[: self.max_message_chars]}...[truncated]"
        return safe

    def _event_record(self, event_type: str, message: str) -> Dict[str, str]:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": str(event_type),
            "message": message,
        }

    def _append_event_record(self, record: Dict[str, str]) -> None:
        if not self.persist:
            return
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            lock_path = self.output_dir / f".{EVENT_LOG_FILENAME}.lock"
            line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            with _FileLock(lock_path):
                with self.event_log_path.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
        except OSError as exc:
            logger.debug(
                "Failed to append pipeline event: %s",
                SecurityValidator.sanitize_log_message(str(exc)),
            )

    def emit(self, event_type: str, message: Any) -> None:
        """
        Emit an event to the stream.
        """
        safe_message = self._sanitize_message(message)
        self._append_event_record(self._event_record(event_type, safe_message))

        if event_type in ("error", "critical"):
            logger.error(f"[{event_type}] {safe_message}")
        elif event_type in ("warning",):
            logger.warning(f"[{event_type}] {safe_message}")
        elif event_type in ("test_success", "fetch_success"):
            logger.debug(f"[{event_type}] {safe_message}")
        else:
            logger.info(f"[{event_type}] {safe_message}")

    async def aclose(self) -> None:
        """
        Asynchronously close the event stream and flush any buffered events.
        """
        self.emit("stream_close", "Event stream closing.")
