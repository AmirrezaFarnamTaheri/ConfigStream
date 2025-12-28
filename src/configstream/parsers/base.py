"""
Base parsing utilities and constants.
Refactored into specific modules for better maintainability.
"""

from .decoders import safe_b64_decode, validate_b64_input  # noqa: F401
from .extraction import extract_config_lines, is_plausible_proxy_config
from .normalization import normalize_proxy_details

# Constants are now in ..constants but re-exported implicitly if used (but they are not exported in original code explicitly, just imported)
# If existing code imports constants from here, it will break.
# Let's check imports in original code.
# Original code imported constants from ..constants.

__all__ = [
    "validate_b64_input",
    "safe_b64_decode",
    "is_plausible_proxy_config",
    "extract_config_lines",
    "normalize_proxy_details",
]
