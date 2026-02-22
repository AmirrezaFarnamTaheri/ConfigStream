# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Output Converter Helpers.
Exposes converters from submodules.
"""

from .singbox import to_singbox_outbound
from .clash import to_clash_proxy
from .common import safe_int_conversion
from .chains import (
    chain_outbounds_from_details,
    extract_chain_proxies,
    update_chain_details,
)

__all__ = [
    "to_singbox_outbound",
    "to_clash_proxy",
    "safe_int_conversion",
    "chain_outbounds_from_details",
    "extract_chain_proxies",
    "update_chain_details",
]
