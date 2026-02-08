# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Dict, Any, Optional
import logging

from ..models import Proxy
from ..tagging import get_flag_emoji
from ..utils.bool_parser import parse_bool, parse_tls_flag

logger = logging.getLogger(__name__)


def to_clash_proxy(proxy: Proxy) -> Optional[Dict[str, Any]]:
    """
    Converts a Proxy object into a Clash proxy dictionary.
    Returns None if the protocol is not supported or conversion fails.
    """
    if not proxy.is_working:
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

        common = {
            "name": name,
            "server": proxy.address,
            "port": proxy.port,
            "type": proxy.protocol,
        }

        if proxy.protocol == "ss" or proxy.protocol == "shadowsocks":
            common["type"] = "ss"
            common["cipher"] = (
                proxy.details.get("method")
                or proxy.details.get("cipher")
                or "chacha20-ietf-poly1305"
            )
            common["password"] = proxy.details.get("password") or proxy.uuid
            # Add plugin support if needed
            if proxy.details.get("plugin"):
                common["plugin"] = proxy.details["plugin"]
                # [FIX] Clash expects plugin-opts as dict, parser may store as string
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

        elif proxy.protocol == "vmess":
            common["uuid"] = proxy.uuid
            # [FIX] Parser stores as "aid", not "alterId"
            common["alterId"] = proxy.details.get("aid", proxy.details.get("alterId", 0))
            common["cipher"] = (
                proxy.details.get("scy") or proxy.details.get("cipher") or "auto"
            )

            # Transport
            # Map 'net' from details (commonly used by some parsers) to 'network'
            net = proxy.details.get("network") or proxy.details.get("net") or "tcp"
            common["network"] = net
            if net == "ws":
                common["ws-opts"] = {
                    "path": proxy.details.get("path", "/"),
                    "headers": {"Host": proxy.details.get("host", "")},
                }
            elif net == "grpc":
                common["grpc-opts"] = {
                    "grpc-service-name": proxy.details.get("serviceName", "")
                }

            # TLS
            tls_enabled = parse_tls_flag(proxy.details.get("tls")) or proxy.details.get(
                "security"
            ) in ("tls", "reality")
            if tls_enabled:
                common["tls"] = True
                if proxy.details.get("sni"):
                    common["servername"] = proxy.details["sni"]
                if proxy.details.get("fp"):
                    common["client-fingerprint"] = proxy.details["fp"]

            return common

        elif proxy.protocol == "trojan":
            common["password"] = proxy.uuid
            # [FIX] Trojan inherently uses TLS; always set tls and udp
            common["tls"] = True
            common["udp"] = True
            if proxy.details.get("sni"):
                common["sni"] = proxy.details["sni"]
            if proxy.details.get("fp"):
                common["client-fingerprint"] = proxy.details["fp"]
            return common

        # Basic VLESS support (Clash Meta/Premium only usually, but often mapped)
        elif proxy.protocol == "vless":
            common["uuid"] = proxy.uuid
            common["flow"] = proxy.details.get("flow", "")

            # Transport & TLS similar to VMess
            # [FIX] Also check "net" and "type" keys (parsers use different keys)
            net = proxy.details.get("network") or proxy.details.get("net") or proxy.details.get("type") or "tcp"
            common["network"] = net
            if net == "ws":
                common["ws-opts"] = {
                    "path": proxy.details.get("path", "/"),
                    "headers": {"Host": proxy.details.get("host", "")},
                }
            # Add VLESS gRPC support (was missing - only VMess had it)
            elif net == "grpc":
                common["grpc-opts"] = {
                    "grpc-service-name": proxy.details.get("serviceName", "")
                }

            # TLS handling
            security = proxy.details.get("security")
            if security == "reality":
                # Clash Meta specific Reality fields
                common["tls"] = True
                common["servername"] = proxy.details.get("sni", "")
                common["reality-opts"] = {
                    "public-key": proxy.details.get("pbk", ""),
                    "short-id": proxy.details.get("sid", ""),
                }
                if proxy.details.get("fp"):
                    common["client-fingerprint"] = proxy.details["fp"]
            else:
                tls_enabled = (
                    parse_tls_flag(proxy.details.get("tls")) or security == "tls"
                )
                if tls_enabled:
                    common["tls"] = True
                    if proxy.details.get("sni"):
                        common["servername"] = proxy.details["sni"]
                    if proxy.details.get("fp"):
                        common["client-fingerprint"] = proxy.details["fp"]

            return common

        # Clash Meta (Mihomo) Support for modern protocols
        elif proxy.protocol == "hysteria2":
            common["type"] = "hysteria2"
            common["password"] = proxy.uuid or proxy.details.get("password", "")
            common["sni"] = proxy.details.get("sni", "")
            common["skip-cert-verify"] = parse_bool(
                proxy.details.get("allowInsecure", False)
            )
            if proxy.details.get("obfs") == "salamander":
                common["obfs"] = "salamander"
                common["obfs-password"] = proxy.details.get("obfs-password", "")
            return common

        elif proxy.protocol == "tuic":
            common["type"] = "tuic"
            common["uuid"] = proxy.uuid
            common["password"] = proxy.details.get("password", "")
            common["sni"] = proxy.details.get("sni", "")
            common["congestion-controller"] = proxy.details.get(
                "congestion_controller", "bbr"
            )
            common["skip-cert-verify"] = parse_bool(
                proxy.details.get("allowInsecure", False)
            )
            return common

        elif proxy.protocol == "wireguard":
            common["type"] = "wireguard"
            # Safely get the first IP or fall back to a default
            local_addresses = proxy.details.get("local_address")
            if (
                local_addresses
                and isinstance(local_addresses, list)
                and local_addresses
            ):
                common["ip"] = local_addresses[0]
            else:
                common["ip"] = "172.16.0.2"

            common["private-key"] = proxy.details.get("private_key", "")
            common["public-key"] = proxy.details.get("peer_public_key", "")
            if "reserved" in proxy.details:
                common["reserved"] = proxy.details["reserved"]
            if "mtu" in proxy.details:
                try:
                    common["mtu"] = int(proxy.details["mtu"])
                except (TypeError, ValueError):
                    pass
            common["udp"] = True
            return common

        # Fallback or unknown
        return None

    except Exception as e:
        logger.debug(f"Failed to convert proxy {proxy.id} to Clash: {e}")
        return None
