# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sanitized, bounded, batched JSONL pipeline event persistence."""

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
    DEFAULT_QUEUE_CAPACITY = 4096

    def __init__(
        self,
        output_dir: Path,
        *,
        persist: bool = True,
        max_message_chars: int = 2000,
        queue_capacity: int = DEFAULT_QUEUE_CAPACITY,
    ):
        if queue_capacity <= 0:
            raise ValueError("queue_capacity must be positive")
        self.output_dir = Path(output_dir)
        self.persist = bool(persist)
        self.max_message_chars = max(256, int(max_message_chars))
        self.event_log_path = self.output_dir / EVENT_LOG_FILENAME
        self.queue: queue.Queue[Any] = queue.Queue(maxsize=int(queue_capacity))
        self._shutdown_sentinel = object()
        self._closed = False
        self._writer_thread: threading.Thread | None = None
        self._dropped_events = 0
        self._drop_lock = threading.Lock()
        if self.persist:
            self._writer_thread = threading.Thread(
                target=self._write_loop,
                name="EventStreamWriter",
                daemon=True,
            )
            self._writer_thread.start()

    @property
    def dropped_events(self) -> int:
        with self._drop_lock:
            return self._dropped_events

    def _record_drop(self) -> None:
        with self._drop_lock:
            self._dropped_events += 1

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
                logger.error(
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

    def _append_event_record(self, record: Dict[str, str]) -> bool:
        if not self.persist or self._closed:
            return False
        try:
            self.queue.put_nowait(record)
            return True
        except queue.Full:
            self._record_drop()
            return False

    def emit(self, event_type: str, message: Any) -> bool:
        safe_message = self._sanitize_message(message)
        persisted = self._append_event_record(
            self._event_record(event_type, safe_message)
        )
        rendered = f"[{event_type}] {safe_message}"
        if event_type in {"error", "critical"}:
            logger.error(rendered)
        elif event_type == "warning":
            logger.warning(rendered)
        elif event_type in {"test_success", "fetch_success"}:
            logger.debug(rendered)
        else:
            logger.info(rendered)
        if self.persist and not persisted and not self._closed:
            logger.warning(
                "Event queue full; dropped telemetry event (total dropped=%d)",
                self.dropped_events,
            )
        return persisted

    async def aclose(self, *, timeout_seconds: float = 5.0) -> None:
        if self._closed:
            return
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        self.emit("stream_close", "Event stream closing.")
        self._closed = True
        if not self.persist or not self._writer_thread:
            return

        # Ensure the shutdown marker is delivered even when the queue is full.
        loop = asyncio.get_running_loop()
        try:
            await asyncio.wait_for(
                loop.run_in_executor(None, self.queue.put, self._shutdown_sentinel),
                timeout=timeout_seconds,
            )
            await asyncio.wait_for(
                loop.run_in_executor(None, self._writer_thread.join),
                timeout=timeout_seconds,
            )
        except (asyncio.TimeoutError, RuntimeError):
            logger.error(
                "Event stream shutdown exceeded %.2fs; %d event(s) were dropped",
                timeout_seconds,
                self.dropped_events,
            )
