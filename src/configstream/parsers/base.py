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
from .validation import (
    validate_host,
    validate_port,
    validate_host_port,
    record_rejection,
    get_rejection_stats,
    reset_rejection_stats,
    log_rejection_summary,
)

__all__ = [
    "validate_b64_input",
    "safe_b64_decode",
    "is_plausible_proxy_config",
    "extract_config_lines",
    "normalize_proxy_details",
    "validate_host",
    "validate_port",
    "validate_host_port",
    "record_rejection",
    "get_rejection_stats",
    "reset_rejection_stats",
    "log_rejection_summary",
]
