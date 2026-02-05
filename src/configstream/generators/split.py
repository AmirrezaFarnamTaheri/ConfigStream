# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import json
import copy
from pathlib import Path
from typing import List, Dict, Any, Set, Optional

from ..models import Proxy
from .clash import generate_clash_config
from ..converters import to_singbox_outbound
from ..utils import AtomicFileWriter
from ..dns_profiles import build_singbox_dns_profile

logger = logging.getLogger(__name__)


def _strip_internal_metadata(outbounds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Strip internal metadata fields (starting with '_') from outbounds.
    """
    cleaned = []
    for ob in outbounds:
        clean_ob = {k: v for k, v in ob.items() if not k.startswith("_")}
        cleaned.append(clean_ob)
    return cleaned


def _append_unique_tag(tags: List[str], tag: Optional[str]) -> None:
    if tag and tag not in tags:
        tags.append(tag)


def _chain_entry_tag(chain: List[Dict[str, Any]]) -> Optional[str]:
    for item in reversed(chain):
        tag = item.get("tag")
        if tag:
            return tag
    return None


def _is_washed_proxy(proxy: Proxy, washed_ids: Optional[Set[str]]) -> bool:
    if not washed_ids:
        return False
    if proxy.id in washed_ids:
        return True
    if isinstance(proxy.details, dict):
        origin_id = proxy.details.get("_origin_id")
        if origin_id in washed_ids:
            return True
    return False


def generate_split_outputs(
    proxies: List[Proxy],
    output_dir: Path,
    washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    washed_ids: Optional[Set[str]] = None,
    smart_chains: Optional[Dict[str, List[List[Dict[str, Any]]]]] = None,
    name_suffix: str = "",
    key_suffix: str = "",
    singbox_dns_profile: Optional[Dict[str, Any]] = None,
    clash_dns_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Path]:
    """
    Generates split outputs (Tank/Sniper strategies) and Clash.
    Updated to match V2RayN format.
    """
    files: Dict[str, Path] = {}
    suffix = f"-{name_suffix}" if name_suffix else ""
    key_suffix_str = f"_{key_suffix}" if key_suffix else ""

    # Ensure DNS profile is robust if not provided
    if singbox_dns_profile is None:
        singbox_dns_profile = build_singbox_dns_profile()

    # Selector tag consistent with SingBoxGenerator and V2RayN example
    SELECTOR_TAG = "🌍 Proxy Select"
    AUTO_TAG = "⚡ Best Latency"

    # 1. Sniper (Standard singbox.json) - Smart Routing + TLS Fragmentation
    outbounds: List[Dict[str, Any]] = []
    selector_tags: List[str] = []

    for p in proxies:
        if _is_washed_proxy(p, washed_ids):
            continue

        chain_outbounds = p.details.get("chain_outbounds")
        if isinstance(chain_outbounds, list) and chain_outbounds:
            chain_copy = copy.deepcopy(chain_outbounds)
            outbounds.extend(chain_copy)
            _append_unique_tag(selector_tags, _chain_entry_tag(chain_copy))
            continue

        sb_proxy = to_singbox_outbound(p)
        if sb_proxy:
            tag = p.remarks or f"{p.protocol}-{p.id[:8]}"
            sb_proxy["tag"] = tag

            # Inject evasion features
            from configstream.intelligence.evasion import enrich_outbound_with_evasion
            from configstream.config import AppSettings
            settings = AppSettings()
            evasion_mode = getattr(settings, "EVASION_MODE", "aggressive").lower()
            
            enable_utls = evasion_mode in ("aggressive", "stealth")
            enable_alpn = evasion_mode == "aggressive"
            enable_fragmentation = evasion_mode in ("aggressive", "stealth")
            enable_multiplexing = evasion_mode == "aggressive"

            sb_proxy = enrich_outbound_with_evasion(
                sb_proxy,
                p.id,
                enable_utls=enable_utls,
                enable_alpn=enable_alpn,
                enable_fragmentation=enable_fragmentation,
                enable_multiplexing=enable_multiplexing,
            )
            outbounds.append(sb_proxy)
            _append_unique_tag(selector_tags, tag)

    if washed_outbounds:
        washed_clones = copy.deepcopy(washed_outbounds)
        outbounds.extend(washed_clones)
        for w in washed_clones:
            if w.get("tag") and "RELAY" not in w["tag"]:
                _append_unique_tag(selector_tags, w["tag"])

    if smart_chains:
        for chain_list in smart_chains.values():
            for chain in chain_list:
                chain_copy = copy.deepcopy(chain)
                outbounds.extend(chain_copy)
                _append_unique_tag(selector_tags, _chain_entry_tag(chain_copy))
                for item in chain_copy:
                    if item.get("type") in ("selector", "urltest") and item.get("tag"):
                        _append_unique_tag(selector_tags, item["tag"])

    # Build Selectors
    if selector_tags:
        outbounds.append(
            {
                "type": "urltest",
                "tag": AUTO_TAG,
                "outbounds": selector_tags,
                "url": "http://www.gstatic.com/generate_204",
                "interval": "10m",
                "tolerance": 50,
            }
        )
        outbounds.append(
            {
                "type": "selector",
                "tag": SELECTOR_TAG,
                "outbounds": [AUTO_TAG] + selector_tags,
                "default": AUTO_TAG,
                "interrupt_exist_connections": True,
            }
        )
        # Compatibility aliases
        outbounds.append(
            {
                "type": "urltest",
                "tag": "🚀 Auto", # Legacy name
                "outbounds": selector_tags,
                "url": "http://cp.cloudflare.com/generate_204",
                "interval": "10m",
            }
        )

    clean_outbounds = _strip_internal_metadata(outbounds)

    if not any(o.get("tag") == "direct" for o in clean_outbounds):
        clean_outbounds.append({"type": "direct", "tag": "direct"})
    if not any(o.get("tag") == "dns-out" for o in clean_outbounds):
        clean_outbounds.append({"type": "dns", "tag": "dns-out"})
    if not any(o.get("tag") == "block" for o in clean_outbounds):
        clean_outbounds.append({"type": "block", "tag": "block"})

    # Common Configuration Parts (aligned with e1.json)
    route_config = {
        "default_domain_resolver": {
            "server": "direct_dns",
            "strategy": ""
        },
        "rules": [
            {"action": "sniff"},
            {"protocol": ["dns"], "action": "hijack-dns"},
            {"outbound": "direct", "clash_mode": "Direct"},
            {"outbound": SELECTOR_TAG, "clash_mode": "Global"},
            {"outbound": "direct", "ip_cidr": ["8.8.8.8"]},
            {"network": ["udp"], "port": [443], "action": "reject"},
            {"outbound": "direct", "protocol": ["bittorrent"]},
            {"rule_set": ["geosite-category-ads-all"], "action": "reject"},
            {"outbound": "direct", "ip_is_private": True},
            {"outbound": "direct", "rule_set": ["geosite-private", "geosite-ir", "geoip-ir"]},
            {"outbound": SELECTOR_TAG, "port_range": ["0:65535"]}
        ],
        "rule_set": [
            {
                "tag": "geosite-category-ads-all",
                "type": "remote",
                "format": "binary",
                "url": "https://github.com/SagerNet/sing-geosite/raw/rule-set/geosite-category-ads-all.srs",
                "download_detour": SELECTOR_TAG
            },
            {
                "tag": "geosite-private",
                "type": "remote",
                "format": "binary",
                "url": "https://github.com/SagerNet/sing-geosite/raw/rule-set/geosite-private.srs",
                "download_detour": SELECTOR_TAG
            },
            {
                "tag": "geosite-ir",
                "type": "remote",
                "format": "binary",
                "url": "https://github.com/SagerNet/sing-geosite/raw/rule-set/geosite-ir.srs",
                "download_detour": SELECTOR_TAG
            },
            {
                "tag": "geoip-ir",
                "type": "remote",
                "format": "binary",
                "url": "https://github.com/SagerNet/sing-geoip/raw/rule-set/geoip-ir.srs",
                "download_detour": SELECTOR_TAG
            }
        ],
        "final": SELECTOR_TAG
    }

    experimental_config = {
        "cache_file": {
            "enabled": True,
            "path": "cache.db",
            "store_fakeip": False
        },
        "clash_api": {
            "external_controller": "127.0.0.1:10813"
        }
    }

    sniper_config = {
        "log": {"level": "warn", "timestamp": True},
        "inbounds": [
            {
                "type": "mixed",
                "tag": "socks",
                "listen": "127.0.0.1",
                "listen_port": 10808,
                "sniff": True
            }
        ],
        "outbounds": clean_outbounds,
        "dns": copy.deepcopy(singbox_dns_profile),
        "route": route_config,
        "experimental": experimental_config
    }

    sniper_path = output_dir / f"singbox{suffix}.json"
    AtomicFileWriter.write_text(
        sniper_path, json.dumps(sniper_config, indent=2, ensure_ascii=False)
    )
    files[f"singbox{key_suffix_str}"] = sniper_path

    # 2. Tank (singbox-vpn.json) - Full VPN/TUN
    tank_outbounds: List[Dict[str, Any]] = []
    tank_proxy_tags: List[str] = []

    # Re-convert for Tank (clean slate)
    for p in proxies:
        if _is_washed_proxy(p, washed_ids):
            continue

        chain_outbounds = p.details.get("chain_outbounds")
        if isinstance(chain_outbounds, list) and chain_outbounds:
            chain_copy = copy.deepcopy(chain_outbounds)
            tank_outbounds.extend(chain_copy)
            _append_unique_tag(tank_proxy_tags, _chain_entry_tag(chain_copy))
            continue

        sb_proxy = to_singbox_outbound(p)
        if sb_proxy:
            tag = p.remarks or f"{p.protocol}-{p.id[:8]}"
            sb_proxy["tag"] = tag
            tank_outbounds.append(sb_proxy)
            _append_unique_tag(tank_proxy_tags, tag)

    if washed_outbounds:
        tank_outbounds.extend(copy.deepcopy(washed_outbounds))

    if smart_chains:
        for chain_list in smart_chains.values():
            for chain in chain_list:
                chain_copy = copy.deepcopy(chain)
                tank_outbounds.extend(chain_copy)
                _append_unique_tag(tank_proxy_tags, _chain_entry_tag(chain_copy))

    # Groups
    tank_washed_tags = [
        w["tag"] for w in tank_outbounds if w.get("tag") and "Secure" in w["tag"]
    ]
    if tank_washed_tags:
        tank_outbounds.append(
            {
                "type": "urltest",
                "tag": "🛡️ Washed",
                "outbounds": tank_washed_tags,
                "url": "http://cp.cloudflare.com/generate_204",
                "interval": "10m",
            }
        )

    # Main Selector
    main_options = [AUTO_TAG]
    if tank_washed_tags:
        main_options.append("🛡️ Washed")
    main_options.extend(tank_proxy_tags)

    existing_tags = set(o.get("tag") for o in tank_outbounds)
    main_options = [t for t in main_options if t in existing_tags]

    # Add Auto group
    if tank_proxy_tags:
        tank_outbounds.append(
            {
                "type": "urltest",
                "tag": AUTO_TAG,
                "outbounds": tank_proxy_tags,
                "url": "http://cp.cloudflare.com/generate_204",
                "interval": "10m",
            }
        )
        # Compatibility Alias for Tank
        tank_outbounds.append(
            {
                "type": "urltest",
                "tag": "🚀 Auto",
                "outbounds": tank_proxy_tags,
                "url": "http://cp.cloudflare.com/generate_204",
                "interval": "10m",
            }
        )

    tank_outbounds.append(
        {
            "type": "selector",
            "tag": SELECTOR_TAG,
            "outbounds": main_options,
            "default": AUTO_TAG if AUTO_TAG in main_options else None,
        }
    )

    if not any(o.get("tag") == "direct" for o in tank_outbounds):
        tank_outbounds.append({"type": "direct", "tag": "direct"})
    if not any(o.get("tag") == "dns-out" for o in tank_outbounds):
        tank_outbounds.append({"type": "dns", "tag": "dns-out"})
    if not any(o.get("tag") == "block" for o in tank_outbounds):
        tank_outbounds.append({"type": "block", "tag": "block"})

    clean_tank_outbounds = _strip_internal_metadata(tank_outbounds)

    tank_config = {
        "log": {"level": "info"},
        "inbounds": [
            {
                "type": "tun",
                "tag": "tun-in",
                "interface_name": "tun0",
                "inet4_address": "172.19.0.1/30",
                "auto_route": True,
                "strict_route": True,
            }
        ],
        "outbounds": clean_tank_outbounds,
        "dns": copy.deepcopy(singbox_dns_profile),
        "route": route_config, # Share route config but might need tweaking for TUN
        "experimental": experimental_config
    }

    tank_path = output_dir / f"singbox-vpn{suffix}.json"
    AtomicFileWriter.write_text(
        tank_path, json.dumps(tank_config, indent=2, ensure_ascii=False)
    )
    files[f"singbox_vpn{key_suffix_str}"] = tank_path

    # Clash
    clash_content = generate_clash_config(proxies, dns_profile=clash_dns_profile)
    if clash_content:
        clash_path = output_dir / f"clash{suffix}.yaml"
        AtomicFileWriter.write_text(clash_path, clash_content)
        files[f"clash{key_suffix_str}"] = clash_path

    return files
