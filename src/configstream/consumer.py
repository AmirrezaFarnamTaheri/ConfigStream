# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Backward-compatible forwarder for legacy consumer attributes.
"""

from configstream.auto_detect import auto_detect_and_parse as parse_config
from configstream.security_validator import validate_batch_configs

__all__ = ["parse_config", "validate_batch_configs"]
