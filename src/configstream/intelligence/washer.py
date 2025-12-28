"""
Proxy Washing and Chaining Intelligence.
Refactored into `src/configstream/intelligence/washer/` for modularity.
This module now serves as a facade for backward compatibility.
"""

from .chaining import create_chain, generate_smart_chains
from .washer.core import CLEAN_IP_SOURCES, DEFAULT_CLEAN_IPS, ProxyWasher

__all__ = [
    "ProxyWasher",
    "generate_smart_chains",
    "create_chain",
    "CLEAN_IP_SOURCES",
    "DEFAULT_CLEAN_IPS",
]
