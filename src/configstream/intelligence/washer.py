"""
Proxy Washing and Chaining Intelligence.
Refactored into `src/configstream/intelligence/washer/` for modularity.
This module now serves as a facade for backward compatibility.
"""

from configstream.intelligence.washer.core import (
    ProxyWasher,
    CLEAN_IP_SOURCES,
    DEFAULT_CLEAN_IPS,
)
from configstream.intelligence.chaining import generate_smart_chains, create_chain

__all__ = [
    "ProxyWasher",
    "generate_smart_chains",
    "create_chain",
    "CLEAN_IP_SOURCES",
    "DEFAULT_CLEAN_IPS",
]
