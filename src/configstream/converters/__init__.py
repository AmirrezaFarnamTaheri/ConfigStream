"""
Output Converter Helpers.
Exposes converters from submodules.
"""

from .clash import to_clash_proxy
from .common import safe_int_conversion
from .singbox import to_singbox_outbound

# For backward compatibility with imports that used to import from converters.py
_safe_int_conversion = safe_int_conversion

__all__ = [
    "to_singbox_outbound",
    "to_clash_proxy",
    "safe_int_conversion",
    "_safe_int_conversion",
]
