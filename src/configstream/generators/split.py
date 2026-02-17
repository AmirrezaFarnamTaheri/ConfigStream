# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import json
import copy
from pathlib import Path
from typing import List, Dict, Any, Set, Optional, Tuple

from ..models import Proxy
from .clash import generate_clash_config
from ..converters import to_singbox_outbound
from ..utils import AtomicFileWriter

logger = logging.getLogger(__name__)


def _strip_internal_metadata(outbounds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Strip internal metadata fields (starting with '_') from outbounds.
    These fields are used for internal tracking but are not valid Sing-box fields.

    Fixes: unmarshal error: [SingboxParser] outbounds[X]._process: json: "unknown field "_process"
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
    """
    files: Dict[str, Path] = {}
    suffix = f"-{name_suffix}" if name_suffix else ""
    key_suffix_str = f"_{key_suffix}" if key_suffix else ""

    # 1. Pre-compute base outbound conversions (used by both Sniper and Tank)
    # This avoids calling to_singbox_outbound twice per proxy.
    from configstream.intelligence.evasion import enrich_outbound_with_evasion
    from configstream.config import AppSettings

    _split_settings = AppSettings()
    evasion_mode = getattr(_split_settings, "EVASION_MODE", "aggressive").lower()

    # Cache: proxy.id -> (tag, base_outbound_dict)
    _base_outbound_cache: Dict[str, Tuple[str, Dict[str, Any]]] = {}
    for p in proxies:
        if _is_washed_proxy(p, washed_ids):
            continue
        chain_outbounds = p.details.get("chain_outbounds")
        if isinstance(chain_outbounds, list) and chain_outbounds:
            continue  # chains handled separately
        sb_proxy = to_singbox_outbound(p)
        if sb_proxy:
            tag = p.remarks or f"{p.protocol}-{p.id[:8]}"
            sb_proxy["tag"] = tag
            _base_outbound_cache[p.id] = (tag, sb_proxy)

    # Sniper (Standard singbox.json) - Smart Routing + TLS Fragmentation
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

        cached = _base_outbound_cache.get(p.id)
        if not cached:
            continue
        tag, base_ob = cached
        # Deep copy for Sniper (evasion will mutate)
        sb_proxy = copy.deepcopy(base_ob)

        # Inject evasion features based on configured mode
        if evasion_mode == "aggressive":
            sb_proxy = enrich_outbound_with_evasion(
                sb_proxy,
                p.id,
                enable_utls=True,
                enable_alpn=True,
                enable_fragmentation=True,
                enable_multiplexing=True,
            )
        elif evasion_mode == "stealth":
            sb_proxy = enrich_outbound_with_evasion(
                sb_proxy,
                p.id,
                enable_utls=True,
                enable_alpn=False,
                enable_fragmentation=True,
                enable_multiplexing=False,
            )
        else:  # standard - no evasion (compatibility mode)
            sb_proxy = enrich_outbound_with_evasion(
                sb_proxy,
                p.id,
                enable_utls=False,
                enable_alpn=False,
                enable_fragmentation=False,
                enable_multiplexing=False,
            )
        # Mark evasion features based on actual mode, not unconditionally True
        if not p.details:
            p.details = {}
        p.details["has_utls"] = evasion_mode in ("aggressive", "stealth")
        p.details["has_fragmentation"] = evasion_mode in ("aggressive", "stealth")
        p.details["has_multiplexing"] = evasion_mode == "aggressive"
        p.details["has_alpn_rotation"] = evasion_mode == "aggressive"
        outbounds.append(sb_proxy)
        _append_unique_tag(selector_tags, tag)

    # Add washed outbounds
    if washed_outbounds:
        # Clone to avoid mutating shared objects
        washed_clones = copy.deepcopy(washed_outbounds)
        outbounds.extend(washed_clones)
        for w in washed_clones:
            if w.get("tag") and "RELAY" not in w["tag"]:
                _append_unique_tag(selector_tags, w["tag"])

    # Add Smart Chains to Sniper as well (if available)
    # Ensure smart chains appear in singbox.json
    if smart_chains:
        for chain_list in smart_chains.values():
            for chain in chain_list:
                # Add chain outbounds to Sniper list
                chain_copy = copy.deepcopy(chain)
                outbounds.extend(chain_copy)
                _append_unique_tag(selector_tags, _chain_entry_tag(chain_copy))
                # Add selector tags for chain entry points
                # Chain entry point is usually the first element or a selector wrapping it?
                # Usually chains are [Proxy, Proxy...] or [Selector, UrlTest...]
                # We need to find the "entry point" tag of the chain to add to main selector.
                # Assuming the last element's tag or a specific tag convention?
                # Actually, `chain` is a list of outbounds. They are already linked by tags.
                # The user typically wants to select the "Head" of the chain.
                # In `tank`, we just add them.
                # For `sniper` (Selector based), we should add the chain head to `selector_tags`.
                # But identifying the head is tricky without knowing the structure.
                # However, usually chains have a main "Selector" or "URLTest" at the top level?
                # If `chain` contains a "Selector" or "URLTest" with a tag, we add it.
                for item in chain_copy:
                    if item.get("type") in ("selector", "urltest") and item.get("tag"):
                        _append_unique_tag(selector_tags, item["tag"])

    # Add URLTest
    if selector_tags:
        outbounds.append(
            {
                "type": "urltest",
                "tag": "🚀 Auto",
                "outbounds": selector_tags,
                "url": "http://cp.cloudflare.com/generate_204",
                "interval": "10m",
            }
        )
        outbounds.append(
            {
                "type": "selector",
                "tag": "🌍 Proxy Select",  # Sniper usually uses this too? Or just "🚀 Auto"?
                "outbounds": ["🚀 Auto"] + selector_tags,
                "default": "🚀 Auto",
            }
        )
        # Add "🛡️ Auto-Fallback" alias
        outbounds.append(
            {
                "type": "urltest",
                "tag": "🛡️ Auto-Fallback",
                "outbounds": selector_tags,
                "url": "http://cp.cloudflare.com/generate_204",
                "interval": "10m",
            }
        )
        # Add "🚀 Mode Selector" alias
        outbounds.append(
            {
                "type": "selector",
                "tag": "🚀 Mode Selector",
                "outbounds": ["🚀 Auto", "🛡️ Auto-Fallback"] + selector_tags,
                "default": "🚀 Auto",
            }
        )

    # Strip internal metadata fields (like _process) before serializing
    # These fields cause Sing-box parse errors: "unknown field "_process""
    clean_outbounds = _strip_internal_metadata(outbounds)

    # Ensure essential outbounds exist (required by sing-box / v2rayN / NekoRay)
    if not any(o.get("tag") == "direct" for o in clean_outbounds):
        clean_outbounds.append({"type": "direct", "tag": "direct"})
    if not any(o.get("tag") == "block" for o in clean_outbounds):
        clean_outbounds.append({"type": "block", "tag": "block"})
    if not any(o.get("tag") == "dns-out" for o in clean_outbounds):
        clean_outbounds.append({"type": "dns", "tag": "dns-out"})

    sniper_config = {
        "log": {"level": "info", "timestamp": True},
        "inbounds": [
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "127.0.0.1",
                "listen_port": 2080,
            }
        ],
        "outbounds": clean_outbounds,
    }
    if singbox_dns_profile:
        sniper_config["dns"] = copy.deepcopy(singbox_dns_profile)

    sniper_path = output_dir / f"singbox{suffix}.json"
    AtomicFileWriter.write_text(
        sniper_path, json.dumps(sniper_config, indent=2, ensure_ascii=False)
    )
    files[f"singbox{key_suffix_str}"] = sniper_path

    # 2. Tank (singbox-vpn.json) - Full VPN/TUN - No Fragmentation (usually)
    tank_outbounds: List[Dict[str, Any]] = []
    tank_proxy_tags: List[str] = []

    # Re-use cached base outbounds for Tank (clean slate, no evasion/frag)
    for p in proxies:
        if _is_washed_proxy(p, washed_ids):
            continue

        chain_outbounds = p.details.get("chain_outbounds")
        if isinstance(chain_outbounds, list) and chain_outbounds:
            chain_copy = copy.deepcopy(chain_outbounds)
            tank_outbounds.extend(chain_copy)
            _append_unique_tag(tank_proxy_tags, _chain_entry_tag(chain_copy))
            continue

        cached = _base_outbound_cache.get(p.id)
        if not cached:
            continue
        tag, base_ob = cached
        # Deep copy so Tank has its own clean instance (no evasion mutations)
        sb_proxy = copy.deepcopy(base_ob)
        tank_outbounds.append(sb_proxy)
        _append_unique_tag(tank_proxy_tags, tag)

    if washed_outbounds:
        tank_outbounds.extend(copy.deepcopy(washed_outbounds))

    if smart_chains:
        for chain_list in smart_chains.values():
            # Flatten chain list if needed, but it seems chain_list is List[List[Dict]]?
            # Actually, `generate_smart_chains` returns Dict[str, List[List[Dict]]].
            # So chain_list is List[List[Dict]]. We need to flatten it or iterate.
            for chain in chain_list:
                chain_copy = copy.deepcopy(chain)
                tank_outbounds.extend(chain_copy)
                _append_unique_tag(tank_proxy_tags, _chain_entry_tag(chain_copy))

    # Add Groups to Tank
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

    tank_intranet_tags = [
        w["tag"]
        for w in tank_outbounds
        if w.get("tag") and "INTRANET" in w["tag"] and "EXIT" in w["tag"]
    ]
    if tank_intranet_tags:
        tank_outbounds.append(
            {
                "type": "urltest",
                "tag": "🇮🇷 Intranet",
                "outbounds": tank_intranet_tags,
                "url": "http://cp.cloudflare.com/generate_204",
                "interval": "5m",
            }
        )

    # Auto Group (Test expects "🚀 Auto" in Tank)
    if tank_proxy_tags:
        tank_outbounds.append(
            {
                "type": "urltest",
                "tag": "🚀 Auto",
                "outbounds": tank_proxy_tags,
                "url": "http://cp.cloudflare.com/generate_204",
                "interval": "10m",
            }
        )

    # Main Selector "🌍 Proxy Select"
    main_options = ["🚀 Auto"]
    if tank_washed_tags:
        main_options.append("🛡️ Washed")
    if tank_intranet_tags:
        main_options.append("🇮🇷 Intranet")
    main_options.extend(tank_proxy_tags)

    # Filter out any missing tags in main_options (e.g. if Auto is empty)
    existing_tags = set(o.get("tag") for o in tank_outbounds)
    main_options = [t for t in main_options if t in existing_tags]

    tank_selector: Dict[str, Any] = {
        "type": "selector",
        "tag": "🌍 Proxy Select",
        "outbounds": main_options,
    }
    if "🚀 Auto" in main_options:
        tank_selector["default"] = "🚀 Auto"
    tank_outbounds.append(tank_selector)

    if not any(o.get("tag") == "direct" for o in tank_outbounds):
        tank_outbounds.append({"type": "direct", "tag": "direct"})
    if not any(o.get("tag") == "block" for o in tank_outbounds):
        tank_outbounds.append({"type": "block", "tag": "block"})
    if not any(o.get("tag") == "dns-out" for o in tank_outbounds):
        tank_outbounds.append({"type": "dns", "tag": "dns-out"})

    # Strip internal metadata fields from tank outbounds too
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
        "route": {
            "rules": [
                {"protocol": "dns", "outbound": "dns-out"},
                {"clash_mode": "Direct", "outbound": "direct"},
                {"clash_mode": "Global", "outbound": "🌍 Proxy Select"},
            ]
        },
    }
    if singbox_dns_profile:
        tank_config["dns"] = copy.deepcopy(singbox_dns_profile)

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
