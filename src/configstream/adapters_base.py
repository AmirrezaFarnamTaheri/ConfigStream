# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Shared logic for Proxy Adapters.
"""

from typing import Dict, Optional, Any


def convert_singbox_outbound_to_surge_string(outbound: Dict[str, Any]) -> Optional[str]:
    """
    Reverse engineer Sing-box outbound dict to Surge string.
    """
    o_type = outbound.get("type")
    server = outbound.get("server")
    port = outbound.get("server_port")
    tag = outbound.get("tag", "proxy")

    if not (server and port):
        return None

    if o_type == "shadowsocks":
        method = outbound.get("method")
        password = outbound.get("password")
        return f"{tag} = ss, {server}, {port}, encrypt-method={method}, password={password}"

    elif o_type == "vmess":
        uuid = outbound.get("uuid")
        return f"{tag} = vmess, {server}, {port}, username={uuid}"

    elif o_type == "vless":
        uuid = outbound.get("uuid")
        sni = ""
        tls = outbound.get("tls") or {}
        if isinstance(tls, dict):
            sni = tls.get("server_name", "")
        sni_part = f", sni={sni}" if sni else ""
        return f"{tag} = vless, {server}, {port}, username={uuid}{sni_part}"

    elif o_type == "trojan":
        password = outbound.get("password", "")
        sni = ""
        tls = outbound.get("tls") or {}
        if isinstance(tls, dict):
            sni = tls.get("server_name", "")
        sni_part = f", sni={sni}" if sni else ""
        return f"{tag} = trojan, {server}, {port}, password={password}{sni_part}"

    elif o_type == "hysteria2":
        password = outbound.get("password", "")
        return f"{tag} = hysteria2, {server}, {port}, password={password}"

    elif o_type == "http":
        return f"{tag} = http, {server}, {port}"

    elif o_type == "socks5":
        return f"{tag} = socks5, {server}, {port}"

    elif o_type == "wireguard":
        ip = outbound.get("server")
        port = outbound.get("server_port")
        priv = outbound.get("private_key")
        pub = outbound.get("peer_public_key")
        mtu = outbound.get("mtu", 1280)
        local_ips = outbound.get("local_address", ["172.16.0.2/32"])
        if not (ip and port and priv and pub):
            return None
        line = f"{tag} = wireguard, {ip}, {port}, private-key={priv}, peer-public-key={pub}, mtu={mtu}"
        if local_ips:
            line += f", addresses={local_ips[0]}"
        return line

    return None


def format_singbox_chain_for_surge(
    exit_node: Dict[str, Any], all_outbounds: list[Dict[str, Any]]
) -> Optional[str]:
    """
    Convert a Sing-box WireGuard-over-Proxy chain to Surge format.
    """
    relay_tag = exit_node.get("detour")
    relay = next((o for o in all_outbounds if o.get("tag") == relay_tag), None)

    if not relay:
        return None

    lines = []
    relay_line = convert_singbox_outbound_to_surge_string(relay)
    if not relay_line:
        return None

    if "=" in relay_line:
        _, details = relay_line.split("=", 1)
        lines.append(f"{relay_tag} = {details.strip()}")
    else:
        return None

    exit_tag = exit_node["tag"]
    ip = "162.159.192.1"
    port = 2408

    if "server" in exit_node:
        ip = exit_node["server"]
    if "server_port" in exit_node:
        port = exit_node["server_port"]

    priv = exit_node.get("private_key")
    pub = exit_node.get("peer_public_key")
    local_ips = exit_node.get("local_address", ["172.16.0.2/32"])

    mtu = exit_node.get("mtu", 1280)
    wg_line = f"{exit_tag} = wireguard, {ip}, {port}, private-key={priv}, peer-public-key={pub}, mtu={mtu}, underlying-proxy={relay_tag}"

    if local_ips:
        wg_line += f", addresses={local_ips[0]}"

    lines.append(wg_line)
    return "\n".join(lines)


def format_singbox_chain_for_loon(
    exit_node: Dict[str, Any], all_outbounds: list[Dict[str, Any]]
) -> Optional[str]:
    """
    Convert a Sing-box WireGuard-over-Proxy chain to Loon format.
    """
    relay_tag = exit_node.get("detour")
    relay = next((o for o in all_outbounds if o.get("tag") == relay_tag), None)

    if not relay:
        return None

    lines = []
    relay_line = convert_singbox_outbound_to_surge_string(relay)

    o_type = relay.get("type")
    if o_type == "shadowsocks":
        server = relay.get("server")
        port = relay.get("server_port")
        method = relay.get("method")
        password = relay.get("password")
        relay_line = (
            f'{relay_tag} = shadowsocks, {server}, {port}, {method}, "{password}"'
        )
    elif o_type == "vmess":
        server = relay.get("server")
        port = relay.get("server_port")
        uuid = relay.get("uuid")
        relay_line = f'{relay_tag} = vmess, {server}, {port}, auto, "{uuid}"'
    elif o_type == "vless":
        server = relay.get("server")
        port = relay.get("server_port")
        uuid = relay.get("uuid")
        relay_line = f'{relay_tag} = vless, {server}, {port}, "{uuid}"'
    elif o_type == "trojan":
        server = relay.get("server")
        port = relay.get("server_port")
        password = relay.get("password", "")
        relay_line = f'{relay_tag} = trojan, {server}, {port}, "{password}"'

    if not relay_line:
        return None
    lines.append(relay_line)

    exit_tag = exit_node["tag"]
    ip = exit_node.get("server", "162.159.192.1")
    port = exit_node.get("server_port", 2408)
    priv = exit_node.get("private_key")
    pub = exit_node.get("peer_public_key")

    mtu = exit_node.get("mtu", 1280)
    wg_line = f"{exit_tag} = wireguard, {ip}, {port}, private-key={priv}, peer-public-key={pub}, mtu={mtu}, proxy={relay_tag}"

    local_ips = exit_node.get("local_address", ["172.16.0.2/32"])
    if local_ips:
        ip_only = local_ips[0].split("/")[0]
        wg_line += f", interface-ip={ip_only}"

    lines.append(wg_line)
    return "\n".join(lines)


def format_shielded_chain_for_surge(
    relay_node: Dict[str, Any], shield_node: Dict[str, Any]
) -> Optional[str]:
    """
    Convert a Shielded Chain (Proxy over WireGuard) to Surge format.
    """
    lines = []

    shield_line = convert_singbox_outbound_to_surge_string(shield_node)
    if not shield_line:
        return None
    lines.append(shield_line)

    relay_tag = relay_node.get("tag")
    shield_tag = shield_node.get("tag")

    base_relay = convert_singbox_outbound_to_surge_string(relay_node)
    if not base_relay:
        return None

    final_relay = f"{base_relay}, underlying-proxy={shield_tag}"
    lines.append(final_relay)

    return "\n".join(lines)


def format_shielded_chain_for_loon(
    relay_node: Dict[str, Any], shield_node: Dict[str, Any]
) -> Optional[str]:
    """
    Convert a Shielded Chain (Proxy over WireGuard) to Loon format.
    """
    lines = []

    s_tag = shield_node.get("tag")
    s_ip = shield_node.get("server")
    s_port = shield_node.get("server_port")
    s_priv = shield_node.get("private_key")
    s_pub = shield_node.get("peer_public_key")
    s_mtu = shield_node.get("mtu", 1280)
    s_local = shield_node.get("local_address", ["172.16.0.2/32"])

    if not (s_ip and s_port and s_priv and s_pub):
        return None

    shield_line = f'{s_tag} = wireguard, {s_ip}, {s_port}, private-key="{s_priv}", peer-public-key="{s_pub}", mtu={s_mtu}'
    if s_local:
        ip_only = s_local[0].split("/")[0]
        shield_line += f", interface-ip={ip_only}"

    lines.append(shield_line)

    r_tag = relay_node.get("tag")
    r_type = relay_node.get("type")
    r_server = relay_node.get("server")
    r_port = relay_node.get("server_port")

    relay_line = None
    if r_type == "vmess":
        uuid = relay_node.get("uuid")
        relay_line = f'{r_tag} = vmess, {r_server}, {r_port}, auto, "{uuid}"'
    elif r_type == "vless":
        uuid = relay_node.get("uuid")
        relay_line = f'{r_tag} = vless, {r_server}, {r_port}, "{uuid}"'
    elif r_type == "trojan":
        pwd = relay_node.get("password")
        relay_line = f'{r_tag} = trojan, {r_server}, {r_port}, "{pwd}"'
    elif r_type == "shadowsocks":
        method = relay_node.get("method")
        pwd = relay_node.get("password")
        relay_line = f'{r_tag} = shadowsocks, {r_server}, {r_port}, {method}, "{pwd}"'

    if relay_line:
        lines.append(f"{relay_line}, proxy={s_tag}")
        return "\n".join(lines)

    return None
