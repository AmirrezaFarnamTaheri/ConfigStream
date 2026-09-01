# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Dict, Any, Optional, Callable
import logging

from ..models import Proxy
from ..security_validator import SecurityValidator
from ..tagging import get_flag_emoji
from ..utils.bool_parser import parse_bool
from .clash_utils import add_transport_opts

logger = logging.getLogger(__name__)

_PROTOCOL_ALIASES = {
    "ss2022": "shadowsocks",
    "hy2": "hysteria2",
    "husi": "hysteria2",
    "exclave": "vless",
    "wg": "wireguard",
}


def _convert_ss(proxy: Proxy, common: Dict[str, Any]) -> Dict[str, Any]:
    common["type"] = "ss"
    common["cipher"] = (
        proxy.details.get("method")
        or proxy.details.get("cipher")
        or "chacha20-ietf-poly1305"
    )
    common["password"] = proxy.details.get("password") or proxy.uuid

    if proxy.details.get("plugin"):
        common["plugin"] = proxy.details["plugin"]
        raw_opts = proxy.details.get("plugin_opts", {})
        if isinstance(raw_opts, str) and raw_opts:
            common["plugin-opts"] = dict(
                item.split("=", 1) for item in raw_opts.split(";") if "=" in item
            )
        elif isinstance(raw_opts, dict):
            common["plugin-opts"] = raw_opts
        else:
            common["plugin-opts"] = {}
    return common


def _convert_vmess(proxy: Proxy, common: Dict[str, Any]) -> Dict[str, Any]:
    common["uuid"] = proxy.uuid
    common["alterId"] = proxy.details.get("aid", proxy.details.get("alterId", 0))
    common["cipher"] = proxy.details.get("scy") or proxy.details.get("cipher") or "auto"
    add_transport_opts(common, proxy.details)
    return common


def _convert_trojan(proxy: Proxy, common: Dict[str, Any]) -> Dict[str, Any]:
    common["password"] = proxy.uuid
    common["udp"] = True
    add_transport_opts(common, proxy.details)
    common["tls"] = True

    if "servername" in common:
        common.setdefault("sni", common.pop("servername"))
    elif proxy.details.get("sni"):
        common["sni"] = proxy.details["sni"]
    return common


def _convert_vless(proxy: Proxy, common: Dict[str, Any]) -> Dict[str, Any]:
    common["uuid"] = proxy.uuid
    flow = proxy.details.get("flow", "")
    if flow:
        common["flow"] = flow
    add_transport_opts(common, proxy.details)
    return common


def _convert_hysteria2(proxy: Proxy, common: Dict[str, Any]) -> Dict[str, Any]:
    common["type"] = "hysteria2"
    common["password"] = (
        proxy.details.get("password", "") or proxy.details.get("auth", "") or proxy.uuid
    )
    common["tls"] = True
    common["sni"] = proxy.details.get("sni", "")
    common["skip-cert-verify"] = parse_bool(proxy.details.get("allowInsecure", False))
    if proxy.details.get("obfs") == "salamander":
        common["obfs"] = "salamander"
        common["obfs-password"] = proxy.details.get("obfs-password", "")
    return common


def _convert_tuic(proxy: Proxy, common: Dict[str, Any]) -> Dict[str, Any]:
    common["type"] = "tuic"
    common["uuid"] = proxy.uuid
    common["password"] = proxy.details.get("password", "")
    common["tls"] = True
    common["sni"] = proxy.details.get("sni", "")
    common["congestion-controller"] = proxy.details.get("congestion_controller", "bbr")
    common["skip-cert-verify"] = parse_bool(proxy.details.get("allowInsecure", False))
    return common


def _convert_socks5(proxy: Proxy, common: Dict[str, Any]) -> Dict[str, Any]:
    common["type"] = "socks5"
    if proxy.details.get("username") and proxy.details.get("password"):
        common["username"] = proxy.details["username"]
        common["password"] = proxy.details["password"]
    common["udp"] = True
    common["tls"] = parse_bool(proxy.details.get("tls", False))
    common["skip-cert-verify"] = parse_bool(
        proxy.details.get("skip_cert_verify", False)
    )
    return common


def _convert_wireguard(proxy: Proxy, common: Dict[str, Any]) -> Dict[str, Any]:
    common["type"] = "wireguard"
    local_addresses = proxy.details.get("local_address")
    if local_addresses and isinstance(local_addresses, list) and local_addresses:
        common["ip"] = local_addresses[0]
    else:
        common["ip"] = "172.16.0.2"

    common["private-key"] = proxy.details.get("private_key", "")
    common["public-key"] = proxy.details.get("peer_public_key", "")
    if "reserved" in proxy.details:
        common["reserved"] = proxy.details["reserved"]

    # Handle MTU safely
    raw_mtu = proxy.details.get("mtu", 1280)
    try:
        common["mtu"] = int(raw_mtu)
    except (TypeError, ValueError):
        common["mtu"] = 1280

    common["udp"] = True
    return common


# Dispatch table for protocol handlers
_PROTOCOL_HANDLERS: Dict[str, Callable[[Proxy, Dict[str, Any]], Dict[str, Any]]] = {
    "ss": _convert_ss,
    "shadowsocks": _convert_ss,
    "vmess": _convert_vmess,
    "trojan": _convert_trojan,
    "vless": _convert_vless,
    "hysteria2": _convert_hysteria2,
    "tuic": _convert_tuic,
    "socks5": _convert_socks5,
    "socks": _convert_socks5,
    "wireguard": _convert_wireguard,
}


def to_clash_proxy(
    proxy: Proxy, ignore_status: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Converts a Proxy object into a Clash proxy dictionary.
    Returns None if the protocol is not supported or conversion fails.
    """
    if not proxy.is_working and not ignore_status:
        return None

    try:
        # Use formatted remarks as name when available (set by ProxyTagger)
        # Fall back to generated name if remarks is empty/generic
        if proxy.remarks and proxy.remarks.lower() not in [
            "",
            "defaultproxyname",
            "none",
        ]:
            name = proxy.remarks
        else:
            flag = get_flag_emoji(proxy.country_code)
            name = f"{flag}-{proxy.protocol}-{proxy.id[:6]}"

        protocol = _PROTOCOL_ALIASES.get((proxy.protocol or "").lower(), proxy.protocol)

        common = {
            "name": name,
            "server": proxy.address,
            "port": proxy.port,
            "type": protocol,
        }

        handler = _PROTOCOL_HANDLERS.get((protocol or "").lower())
        if handler:
            return handler(proxy, common)

        return None

    except Exception as e:
        logger.debug(
            "Failed to convert proxy %s to Clash: %s",
            SecurityValidator.sanitize_log_message(str(proxy.id)),
            SecurityValidator.sanitize_log_message(str(e)),
        )
        return None
