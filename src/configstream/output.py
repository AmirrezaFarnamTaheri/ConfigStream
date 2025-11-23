"""
Output Generation Module (Facade).
Exports functionality from `output_logic`, `output_transport`, and `output_generators`.
Maintains backward compatibility.
"""

from .output_logic import generate_categorized_outputs
from .output_transport import save_json, save_metadata
from .output_generators import generate_split_outputs
from .intelligence.washer import generate_smart_chains, ProxyWasher

__all__ = [
    "generate_categorized_outputs",
    "save_json",
    "save_metadata",
    "generate_split_outputs",
    "generate_smart_chains",
    "ProxyWasher",
]
