# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sanitized, batched JSONL pipeline event persistence."""

import asyncio
import json
import logging
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any, Dict

from configstream.security_validator import SecurityValidator
from configstream.utils import _FileLock

EVENT_LOG_FILENAME = "pipeline_events.jsonl"
logger = logging.getLogger(__name__)


class EventStream:
    FLUSH_BATCH_SIZE = 128
    FLUSH_INTERVAL_SECONDS = 0.1

    def __init__(
        self,
        output_dir: Path,
        *,
        persist: bool = True,
        max_message_chars: int = 2000,
    ):
        self.output_dir = Path(output_dir)
        self.persist = bool(persist)
        self.max_message_chars = max(256, int(max_message_chars))
        self.event_log_path = self.output_dir / EVENT_LOG_FILENAME
        self.queue: queue.Queue[Any] = queue.Queue()
        self._shutdown_sentinel = object()
        self._closed = False
        self._writer_thread: threading.Thread | None = None
        if self.persist:
            self._writer_thread = threading.Thread(
                target=self._write_loop,
                name="EventStreamWriter",
                daemon=True,
            )
            self._writer_thread.start()

    def _flush(self, records: list[Dict[str, str]]) -> None:
        if not records:
            return
        self.output_dir.mkdir(parents=True, exist_ok=True)
        lock_path = self.output_dir / f".{EVENT_LOG_FILENAME}.lock"
        payload = "".join(
            json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
            for record in records
        )
        with _FileLock(lock_path):
            with self.event_log_path.open("a", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()

    def _write_loop(self) -> None:
        stopping = False
        while not stopping:
            first = self.queue.get()
            records: list[Dict[str, str]] = []
            consumed = 1
            if first is self._shutdown_sentinel:
                stopping = True
            else:
                records.append(first)
                deadline = monotonic() + self.FLUSH_INTERVAL_SECONDS
                while len(records) < self.FLUSH_BATCH_SIZE:
                    timeout = deadline - monotonic()
                    if timeout <= 0:
                        break
                    try:
                        item = self.queue.get(timeout=timeout)
                        consumed += 1
                    except queue.Empty:
                        break
                    if item is self._shutdown_sentinel:
                        stopping = True
                        break
                    records.append(item)

            try:
                self._flush(records)
            except OSError as exc:
                logger.warning(
                    "Failed to append pipeline event batch: %s",
                    SecurityValidator.sanitize_log_message(str(exc)),
                )
            finally:
                for _ in range(consumed):
                    self.queue.task_done()

    def _sanitize_message(self, message: Any) -> str:
        safe = SecurityValidator.sanitize_log_message(str(message))
        if len(safe) > self.max_message_chars:
            return f"{safe[: self.max_message_chars]}...[truncated]"
        return safe

    @staticmethod
    def _event_record(event_type: str, message: str) -> Dict[str, str]:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": str(event_type),
            "message": message,
        }

    def _append_event_record(self, record: Dict[str, str]) -> None:
        if self.persist and not self._closed:
            self.queue.put(record)

    def emit(self, event_type: str, message: Any) -> None:
        safe_message = self._sanitize_message(message)
        self._append_event_record(self._event_record(event_type, safe_message))
        if event_type in {"error", "critical"}:
            logger.error("[%s] %s", event_type, safe_message)
        elif event_type == "warning":
            logger.warning("[%s] %s", event_type, safe_message)
        elif event_type in {"test_success", "fetch_success"}:
            logger.debug("[%s] %s", event_type, safe_message)
        else:
            logger.info("[%s] %s", event_type, safe_message)

    async def aclose(self) -> None:
        if self._closed:
            return
        self.emit("stream_close", "Event stream closing.")
        self._closed = True
        if self.persist and self._writer_thread:
            self.queue.put(self._shutdown_sentinel)
            try:
                await asyncio.get_running_loop().run_in_executor(
                    None, self._writer_thread.join
                )
            except RuntimeError:
                self._writer_thread.join()
