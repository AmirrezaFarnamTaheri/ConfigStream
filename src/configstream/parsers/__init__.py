"""
Expose all parsers via a unified interface.
"""

from .base import extract_config_lines
from .generic import parse_generic_url_scheme, parse_naive, parse_v2ray_json
from .openvpn import parse_openvpn
from .others import (parse_brook, parse_hysteria, parse_hysteria2,
                     parse_juicity, parse_snell, parse_ssh, parse_tuic,
                     parse_wireguard, parse_xray)
from .shadowsocks import parse_ss, parse_ss2022
from .ssr import parse_ssr
from .trojan import parse_trojan
from .vless import parse_vless
from .vmess import parse_vmess

# Alias internal names to public ones to maintain compatibility with imports
# accessing via legacy `_parse_*` naming convention.

# For `src/configstream/parsers.py` compatibility:
_extract_config_lines = extract_config_lines
_parse_vmess = parse_vmess
_parse_vless = parse_vless
_parse_ss = parse_ss
_parse_ss2022 = parse_ss2022
_parse_trojan = parse_trojan
_parse_ssr = parse_ssr
_parse_hysteria = parse_hysteria
_parse_hysteria2 = parse_hysteria2
_parse_tuic = parse_tuic
_parse_wireguard = parse_wireguard
_parse_xray = parse_xray
_parse_snell = parse_snell
_parse_brook = parse_brook
_parse_juicity = parse_juicity
_parse_ssh = parse_ssh
_parse_generic_url_scheme = parse_generic_url_scheme
_parse_naive = parse_naive
_parse_v2ray_json = parse_v2ray_json
_parse_openvpn = parse_openvpn
