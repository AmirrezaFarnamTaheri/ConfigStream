# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Output Converter Helpers.
Exposes converters from submodules.
"""

from .singbox import to_singbox_outbound
from .clash import to_clash_proxy
from .common import safe_int_conversion
from .chain_outbounds import chain_obs_from_details
from .chains import extract_chain_proxies, update_chain_details

__all__ = [
    "to_singbox_outbound",
    "to_clash_proxy",
    "safe_int_conversion",
    "chain_obs_from_details",
    "extract_chain_proxies",
    "update_chain_details",
]
