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

    return None


def format_singbox_chain_for_surge(
    exit_node: Dict[str, Any], all_outbounds: list[Dict[str, Any]]
) -> Optional[str]:
    """
    Convert a Sing-box WireGuard-over-Proxy chain to Surge format.
    """
    # 1. Find the Relay
    relay_tag = exit_node.get("detour")
    relay = next((o for o in all_outbounds if o.get("tag") == relay_tag), None)

    if not relay:
        return None

    # 2. Define Relay
    lines = []
    relay_line = convert_singbox_outbound_to_surge_string(relay)
    if not relay_line:
        return None

    if "=" in relay_line:
        _, details = relay_line.split("=", 1)
        lines.append(f"{relay_tag} = {details.strip()}")
    else:
        return None

    # 3. Define Exit (WireGuard)
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

    wg_line = f"{exit_tag} = wireguard, {ip}, {port}, private-key={priv}, peer-public-key={pub}, underlying-proxy={relay_tag}"

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
    # 1. Find the Relay
    relay_tag = exit_node.get("detour")
    relay = next((o for o in all_outbounds if o.get("tag") == relay_tag), None)

    if not relay:
        return None

    # 2. Define Relay
    lines = []
    # Loon uses very similar syntax to Surge for basic proxies
    relay_line = convert_singbox_outbound_to_surge_string(relay)

    # Correction: Loon Shadowsocks syntax is slightly different (no encrypt-method key)
    # Surge: encrypt-method=...
    # Loon: method, "password"

    # Handle Loon specific syntax differences
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

    if not relay_line:
        return None
    lines.append(relay_line)

    # 3. Define Exit (WireGuard)
    exit_tag = exit_node["tag"]
    ip = exit_node.get("server", "162.159.192.1")
    port = exit_node.get("server_port", 2408)
    priv = exit_node.get("private_key")
    pub = exit_node.get("peer_public_key")

    # Loon syntax: ... proxy=RelayName
    wg_line = f"{exit_tag} = wireguard, {ip}, {port}, private-key={priv}, peer-public-key={pub}, proxy={relay_tag}"

    local_ips = exit_node.get("local_address", ["172.16.0.2/32"])
    if local_ips:
        ip_only = local_ips[0].split("/")[0]
        wg_line += f", interface-ip={ip_only}"

    lines.append(wg_line)
    return "\n".join(lines)
