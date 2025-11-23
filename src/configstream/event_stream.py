
import asyncio
from pathlib import Path
from typing import Optional

class EventStream:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        # For now, just a simple logger or no-op if we removed websockets

    def emit(self, event_type: str, message: str):
        # Placeholder for event emission (logs, file append, etc.)
        # print(f"[{event_type}] {message}")
        pass
