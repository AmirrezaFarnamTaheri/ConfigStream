# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Expose all parsers via a unified interface.
"""

from .base import extract_config_lines
from .vmess import parse_vmess
from .vless import parse_vless
from .shadowsocks import parse_ss, parse_ss2022
from .trojan import parse_trojan
from .ssr import parse_ssr
from .tuic import parse_tuic
from .hysteria3 import parse_hysteria3
from .others import (
    parse_hysteria,
    parse_hysteria2,
    parse_wireguard,
    parse_xray,
    parse_snell,
    parse_brook,
    parse_juicity,
    parse_ssh,
)
from .generic import parse_generic_url_scheme, parse_naive, parse_v2ray_json
from .openvpn import parse_openvpn

__all__ = [
    "extract_config_lines",
    "parse_vmess",
    "parse_vless",
    "parse_ss",
    "parse_ss2022",
    "parse_trojan",
    "parse_ssr",
    "parse_hysteria",
    "parse_hysteria2",
    "parse_hysteria3",
    "parse_tuic",
    "parse_wireguard",
    "parse_xray",
    "parse_snell",
    "parse_brook",
    "parse_juicity",
    "parse_ssh",
    "parse_generic_url_scheme",
    "parse_naive",
    "parse_v2ray_json",
    "parse_openvpn",
]
