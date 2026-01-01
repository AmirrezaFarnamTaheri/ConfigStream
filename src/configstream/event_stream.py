# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class EventStream:
    """
    Handles real-time event emission for the pipeline.
    Currently logs events to the standard logger, but designed to support
    WebSocket broadcasting or file-based event streams in the future.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def emit(self, event_type: str, message: str):
        """
        Emit an event to the stream.
        """
        # Log to standard logger for now
        if event_type in ("error", "critical"):
            logger.error(f"[{event_type}] {message}")
        elif event_type in ("warning",):
            logger.warning(f"[{event_type}] {message}")
        elif event_type in ("test_success", "fetch_success"):
            # Demote high-volume success events to DEBUG to reduce log spam
            # These events occur hundreds of times per pipeline run
            logger.debug(f"[{event_type}] {message}")
        else:
            logger.info(f"[{event_type}] {message}")

        # Future: Append to a rotating event log file in output_dir
        # for the frontend to poll if WebSockets are not used.

    async def aclose(self):
        """
        Asynchronously close the event stream and flush any buffered events.
        """
        self.emit("stream_close", "Event stream closing.")
        # Future: Flush buffers if we implement file/network sinks.
