# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Washer Package.
Exposes washing logic.
"""

from .core import ProxyWasher, CLEAN_IP_SOURCES, DEFAULT_CLEAN_IPS

__all__ = [
    "ProxyWasher",
    "CLEAN_IP_SOURCES",
    "DEFAULT_CLEAN_IPS",
]
