# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Output Generation Module (Facade).
Exports functionality from output_logic and related helpers.
"""

from pathlib import Path
import os

from .intelligence.washer import ProxyWasher
from .intelligence.chaining import generate_smart_chains
from .output_logic import generate_categorized_outputs, save_metadata
from .output_transport import save_json

# Global constant for output directory (env override supported)
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "output"))

__all__ = [
    "generate_categorized_outputs",
    "save_json",
    "save_metadata",
    "generate_smart_chains",
    "ProxyWasher",
    "OUTPUT_DIR",
]
