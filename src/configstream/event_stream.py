import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class EventStream:
    """
    A simple file-based event stream for IPC between Worker and Server.
    The worker appends events to a log file.
    The server tails the log file and broadcasts to WebSockets.
    """

    def __init__(self, output_dir: Path):
        self.file_path = output_dir / "events.log"
        self.ensure_file()

    def ensure_file(self):
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self.file_path.touch()

    def emit(self, event_type: str, message: str, data: Optional[dict] = None):
        """Write an event to the stream file."""
        event = {
            "timestamp": time.time(),
            "type": event_type,
            "message": message,
            "data": data or {},
        }
        try:
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Failed to emit event: {e}")

    async def tail(self):
        """Async generator that yields new events from the file."""
        self.ensure_file()
        async with asyncio.Lock():  # Simple lock wrapper if needed, mainly for clarity
            with open(self.file_path, "r", encoding="utf-8") as f:
                # Move to end of file
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if not line:
                        await asyncio.sleep(0.5)
                        continue

                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
