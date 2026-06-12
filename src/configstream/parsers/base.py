# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Base parsing utilities and constants.
Refactored into specific modules for better maintainability.
"""

from .decoders import (
    validate_b64_input,
    safe_b64_decode,
)
from .extraction import is_plausible_proxy_config, extract_config_lines
from .normalization import normalize_proxy_details

__all__ = [
    "validate_b64_input",
    "safe_b64_decode",
    "is_plausible_proxy_config",
    "extract_config_lines",
    "normalize_proxy_details",
]
