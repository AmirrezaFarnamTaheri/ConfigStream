"""
Output Converter Helpers.
Refactored into `src/configstream/converters/` for modularity.
This module now serves as a facade for backward compatibility.
"""

from .converters import (
    to_singbox_outbound,
    to_clash_proxy,
    safe_int_conversion,
    _safe_int_conversion,
)

__all__ = [
    "to_singbox_outbound",
    "to_clash_proxy",
    "safe_int_conversion",
    "_safe_int_conversion",
]
