# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
from typing import List, Any, Optional, Dict

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore

from ..models import Proxy
from ..converters import to_clash_proxy
from ..converters.chains import chain_obs_from_details

logger = logging.getLogger(__name__)


def _unique_name(base_name: str, seen_names: set[str]) -> str:
    """Generate a collision-safe name for Clash entries."""
    candidate = base_name or "Proxy"
    counter = 1
    while candidate in seen_names:
        candidate = f"{base_name}-{counter}"
        counter += 1
    seen_names.add(candidate)
    return candidate


def _proxy_from_chain_outbound(ob: Dict[str, Any], remarks: str) -> Optional[Proxy]:
    """Build a minimal Proxy object from a sing-box outbound."""
    if not isinstance(ob, dict):
        return None
    server = ob.get("server")
    server_port = ob.get("server_port")
    if not server or not server_port:
        return None
    try:
        port = int(server_port)
    except (TypeError, ValueError):
        return None
    if port <= 0 or port > 65535:
        return None

    ob_type = str(ob.get("type", "")).lower()
    proto_map = {
        "shadowsocks": "shadowsocks",
        "vmess": "vmess",
        "vless": "vless",
        "trojan": "trojan",
        "hysteria2": "hysteria2",
        "hysteria": "hysteria",
        "tuic": "tuic",
        "wireguard": "wireguard",
        "http": "http",
        "socks": "socks5",
    }
    protocol = proto_map.get(ob_type)
    if not protocol:
        return None

    details: Dict[str, Any] = {}
    uuid_value = ""

    if protocol == "shadowsocks":
        details["method"] = ob.get("method", "")
        details["password"] = ob.get("password", "")
    elif protocol in ("vmess", "vless"):
        uuid_value = str(ob.get("uuid", ""))
        flow = ob.get("flow")
        if flow:
            details["flow"] = flow
        tls_obj = ob.get("tls")
        if isinstance(tls_obj, dict):
            details["sni"] = tls_obj.get("server_name", "")
            details["tls"] = bool(tls_obj.get("enabled"))
        transport = ob.get("transport")
        if isinstance(transport, dict):
            details["network"] = transport.get("type", "")
            if transport.get("path"):
                details["path"] = transport["path"]
            if transport.get("host"):
                details["host"] = transport["host"]
            if transport.get("service_name"):
                details["serviceName"] = transport["service_name"]
    elif protocol == "trojan":
        uuid_value = str(ob.get("password", ""))
        tls_obj = ob.get("tls")
        if isinstance(tls_obj, dict):
            details["sni"] = tls_obj.get("server_name", "")
            details["tls"] = bool(tls_obj.get("enabled"))
        transport = ob.get("transport")
        if isinstance(transport, dict):
            details["network"] = transport.get("type", "")
            if transport.get("path"):
                details["path"] = transport["path"]
            if transport.get("host"):
                details["host"] = transport["host"]
            if transport.get("service_name"):
                details["serviceName"] = transport["service_name"]
    elif protocol == "hysteria2":
        uuid_value = str(ob.get("password", ""))
        tls_obj = ob.get("tls")
        if isinstance(tls_obj, dict):
            details["sni"] = tls_obj.get("server_name", "")
    elif protocol == "wireguard":
        details["private_key"] = ob.get("private_key", "")
        details["peer_public_key"] = ob.get("peer_public_key", "")
        details["local_address"] = ob.get("local_address", [])
        details["reserved"] = ob.get("reserved", [])
        details["mtu"] = ob.get("mtu", 1280)

    return Proxy(
        config="",
        protocol=protocol,
        address=str(server),
        port=port,
        uuid=uuid_value,
        remarks=remarks,
        details=details,
        is_working=True,
    )


def _origin_proxy_from_revived(proxy: Proxy) -> Optional[Proxy]:
    """Rebuild origin proxy from revived details when available."""
    details = proxy.details or {}
    origin_obj = details.get("origin_proxy")
    if isinstance(origin_obj, dict):
        try:
            return Proxy(**origin_obj)
        except Exception:  # nosec
            pass

    origin_cfg = details.get("origin_config")
    if isinstance(origin_cfg, dict):
        try:
            return Proxy(
                config=str(origin_cfg.get("config", "")),
                protocol=str(origin_cfg.get("protocol", "")),
                address=str(origin_cfg.get("address", "")),
                port=int(origin_cfg.get("port", 0) or 0),
                uuid=str(origin_cfg.get("uuid", "")),
                remarks=str(origin_cfg.get("remarks", "")),
                details=origin_cfg.get("details") or {},
                is_working=True,
            )
        except Exception:  # nosec
            return None
    return None


def _convert_revived(
    proxy: Proxy, seen_names: set[str], ignore_status: bool
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]:
    """
    Convert revived chain proxies into Clash-compatible entries.

    Strategy:
    - Prefer chain_obs and emit relay + warp proxies.
    - Link warp via `dialer-proxy`, and also emit a `relay` group for Mihomo.
    - Fallback to origin proxy conversion when chain details are incomplete.
    """
    generated: List[Dict[str, Any]] = []
    groups: List[Dict[str, Any]] = []
    selected_name: Optional[str] = None
    details = proxy.details or {}

    chain = chain_obs_from_details(details)
    if chain:
        relay_ob: Optional[Dict[str, Any]] = None
        warp_ob: Optional[Dict[str, Any]] = None
        for ob in chain:
            if not isinstance(ob, dict):
                continue
            ob_type = str(ob.get("type", "")).lower()
            if ob_type == "wireguard" and warp_ob is None:
                warp_ob = ob
            elif relay_ob is None:
                relay_ob = ob

        base = proxy.remarks or f"revived-{proxy.id[:8]}"
        relay_proxy = (
            _proxy_from_chain_outbound(relay_ob, f"{base}-relay") if relay_ob else None
        )
        warp_proxy = (
            _proxy_from_chain_outbound(warp_ob, f"{base}-warp") if warp_ob else None
        )

        relay_dict = (
            to_clash_proxy(relay_proxy, ignore_status=True) if relay_proxy else None
        )
        warp_dict = (
            to_clash_proxy(warp_proxy, ignore_status=True) if warp_proxy else None
        )

        relay_name: Optional[str] = None
        warp_name: Optional[str] = None

        if relay_dict:
            relay_name = _unique_name(
                relay_proxy.remarks or f"{base}-relay",  # type: ignore[union-attr]
                seen_names,
            )
            relay_dict["name"] = relay_name
            generated.append(relay_dict)

        if warp_dict:
            warp_name = _unique_name(
                warp_proxy.remarks or f"{base}-warp",  # type: ignore[union-attr]
                seen_names,
            )
            warp_dict["name"] = warp_name
            if relay_name:
                warp_dict["dialer-proxy"] = relay_name
            generated.append(warp_dict)

        if relay_name and warp_name:
            relay_group_name = _unique_name(f"{base}-chain", seen_names)
            groups.append(
                {
                    "name": relay_group_name,
                    "type": "relay",
                    "proxies": [relay_name, warp_name],
                }
            )
            selected_name = relay_group_name
        elif warp_name:
            selected_name = warp_name
        elif relay_name:
            selected_name = relay_name

    if selected_name:
        return generated, groups, selected_name

    origin_proxy = _origin_proxy_from_revived(proxy)
    if origin_proxy:
        converted = to_clash_proxy(origin_proxy, ignore_status=ignore_status)
        if converted:
            origin_name = _unique_name(
                origin_proxy.remarks or (proxy.remarks or f"revived-{proxy.id[:8]}"),
                seen_names,
            )
            converted["name"] = origin_name
            return [converted], [], origin_name

    return [], [], None


def generate_clash_config(
    proxies: List[Proxy],
    extra_outbounds: Any = None,
    dns_profile: Optional[Dict[str, Any]] = None,
    ignore_status: bool = False,
) -> str:
    """
    Generates a Clash YAML configuration.

    Added `extra_outbounds` argument to prevent crash when pipeline passes it.
    However, Clash/Mihomo generator currently only supports standard proxies.
    Chains (WARP-wrapped, revived, shielded) are sing-box only — use
    singbox.json or singbox-chains.json. Mihomo relay does not support
    WireGuard as a hop; use sing-box for chain profiles.
    """
    if not yaml:
        # PyYAML is a normal dependency, but keep a resilient fallback.
        logger.warning("PyYAML not installed; generating a minimal Clash config")
        # Minimal, valid YAML (no proxies).
        lines = [
            "port: 7890",
            "socks-port: 7891",
            "allow-lan: true",
            "mode: Rule",
            "log-level: info",
            "external-controller: 127.0.0.1:9090",
            "proxies: []",
            "proxy-groups:",
            "  - name: PROXY",
            "    type: select",
            "    proxies:",
            "      - DIRECT",
            "rules:",
            "  - MATCH,PROXY",
        ]
        return "\n".join(lines) + "\n"

    proxies_list = []
    proxy_names = []
    extra_groups: List[Dict[str, Any]] = []
    seen_names: set[str] = set()  # Track used names to prevent duplicates

    for p in proxies:
        if p.protocol == "revived" or (p.config or "").startswith("revived://"):
            revived_entries, revived_groups, selected_name = _convert_revived(
                p, seen_names, ignore_status
            )
            if revived_entries:
                proxies_list.extend(revived_entries)
            if revived_groups:
                extra_groups.extend(revived_groups)
            if selected_name:
                proxy_names.append(selected_name)
            continue

        clash_proxy = to_clash_proxy(p, ignore_status=ignore_status)
        if clash_proxy:
            # Generate unique name - avoid tag collisions
            base_name = p.remarks or f"Proxy-{p.id[:8]}"
            unique_name = _unique_name(base_name, seen_names)
            clash_proxy["name"] = unique_name
            proxies_list.append(clash_proxy)
            proxy_names.append(clash_proxy["name"])

    config: dict[str, Any] = {
        "port": 7890,
        "socks-port": 7891,
        "allow-lan": True,
        "mode": "Rule",
        "log-level": "info",
        "external-controller": "127.0.0.1:9090",
        "proxies": proxies_list,
        "proxy-groups": [],
        "rules": ["MATCH,PROXY"],
    }

    if proxy_names:
        dynamic_groups: List[Dict[str, Any]] = [
            {
                "name": "FASTEST",
                "type": "url-test",
                "proxies": proxy_names,
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
            },
            {"name": "PROXY", "type": "select", "proxies": ["FASTEST"] + proxy_names},
        ]
        config["proxy-groups"] = extra_groups + dynamic_groups
    else:
        # Keep the config valid and importable even when no proxies are available.
        # This avoids 404s and "empty file" issues on static hosting.
        logger.info(
            "No valid proxies for Clash config generation; emitting minimal config"
        )
        config["proxy-groups"] = [
            {"name": "PROXY", "type": "select", "proxies": ["DIRECT"]},
        ]

    if dns_profile:
        config["dns"] = dns_profile

    return str(yaml.dump(config, allow_unicode=True, sort_keys=False))
