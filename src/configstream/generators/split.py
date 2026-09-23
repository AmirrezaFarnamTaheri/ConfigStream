# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import json
import copy
from pathlib import Path
from typing import List, Dict, Any, Set, Optional, Tuple

from ..models import Proxy
from .clash import generate_clash_config
from ..converters import to_singbox_outbound
from ..converters.singbox import wireguard_outbound_to_endpoint
from ..converters.chain_outbounds import chain_outbounds_from_details
from ..utils import AtomicFileWriter
from ..dns_profiles import build_singbox_rule_sets

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


def _modernize_singbox_nodes(
    outbounds: List[Dict[str, Any]],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Emit the public sing-box 1.13+ node model before release finalization."""
    modern_outbounds: List[Dict[str, Any]] = []
    endpoints: List[Dict[str, Any]] = []
    for outbound in outbounds:
        kind = outbound.get("type")
        if kind == "wireguard":
            try:
                endpoints.append(wireguard_outbound_to_endpoint(outbound))
            except (TypeError, ValueError):
                logger.debug(
                    "Dropping incompatible WireGuard endpoint from split output"
                )
            continue
        if kind in {"block", "dns"}:
            continue
        modern_outbounds.append(outbound)
    return modern_outbounds, endpoints


def _attach_dns_profile(
    config: Dict[str, Any], profile: Dict[str, Any], use_proxy_detour: bool
) -> None:
    """Keep split DNS rules and their route rule sets together."""
    config["dns"] = copy.deepcopy(profile)
    config.setdefault("experimental", {}).setdefault(
        "cache_file", {"enabled": True, "path": "cache.db", "store_fakeip": False}
    )
    route = config.setdefault("route", {})
    route["default_domain_resolver"] = "local_local"
    route["rule_set"] = build_singbox_rule_sets(
        "🌍 Proxy Select" if use_proxy_detour else "direct"
    )


def _chain_entry_tag(chain: List[Dict[str, Any]]) -> Optional[str]:
    for item in reversed(chain):
        tag = item.get("tag")
        if tag:
            return str(tag)
    return None


def _append_chain_uniquified(
    chain: List[Dict[str, Any]],
    outbounds: List[Dict[str, Any]],
    seen_tags: Set[str],
    tag_remap: Dict[str, str],
    selector_tags: Optional[List[str]] = None,
    *,
    add_all_non_relay: bool = False,
) -> None:
    """
    Append chain outbounds with uniquified tags. Prevents duplicate tags from
    smart chains (chain_tag/warp_tag) or wash_batch (exit_tag) collapsing
    multiple chains into one selectable option.

    When add_all_non_relay=True (flat washed list), add every non-RELAY tag
    to selector. Otherwise add only the last (entry) outbound's tag.
    """
    entry_tag: Optional[str] = None
    for ob in chain:
        if not isinstance(ob, dict):
            continue
        if ob.get("type") in {"block", "dns"}:
            continue
        ob = copy.deepcopy(ob)
        detour = ob.get("detour")
        if isinstance(detour, str) and detour in tag_remap:
            ob["detour"] = tag_remap[detour]
        tag = ob.get("tag")
        if tag and tag in seen_tags:
            suffix = 0
            while f"{tag}-{suffix}" in seen_tags:
                suffix += 1
            new_tag = f"{tag}-{suffix}"
            tag_remap[tag] = new_tag
            tag = new_tag
            ob["tag"] = tag
        outbounds.append(ob)
        if tag:
            seen_tags.add(tag)
            entry_tag = tag
            if add_all_non_relay and "RELAY" not in tag and selector_tags is not None:
                if tag not in selector_tags:
                    selector_tags.append(tag)
    if not add_all_non_relay and selector_tags is not None and entry_tag:
        if entry_tag not in selector_tags:
            selector_tags.append(entry_tag)


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


def _append_tank_groups(
    tank_outbounds: List[Dict[str, Any]],
    tank_proxy_tags: List[str],
) -> bool:
    """Append derived Tank urltest/select groups and report selector availability."""
    tank_outbounds[:] = [
        item for item in tank_outbounds if item.get("type") not in {"block", "dns"}
    ]
    available_tags = {item.get("tag") for item in tank_outbounds}
    tank_proxy_tags[:] = [tag for tag in tank_proxy_tags if tag in available_tags]

    washed_tags = [
        item["tag"]
        for item in tank_outbounds
        if item.get("tag") and "Secure" in item["tag"]
    ]
    if washed_tags:
        tank_outbounds.append(
            {
                "type": "urltest",
                "tag": "🛡️ Washed",
                "outbounds": washed_tags,
                "url": "http://cp.cloudflare.com/generate_204",
                "interval": "10m",
            }
        )

    intranet_tags = [
        item["tag"]
        for item in tank_outbounds
        if item.get("tag") and "INTRANET" in item["tag"] and "EXIT" in item["tag"]
    ]
    if intranet_tags:
        tank_outbounds.append(
            {
                "type": "urltest",
                "tag": "🇮🇷 Intranet",
                "outbounds": intranet_tags,
                "url": "http://cp.cloudflare.com/generate_204",
                "interval": "5m",
            }
        )

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

    main_options = ["🚀 Auto"]
    if washed_tags:
        main_options.append("🛡️ Washed")
    if intranet_tags:
        main_options.append("🇮🇷 Intranet")
    main_options.extend(tank_proxy_tags)

    existing_tags = {item.get("tag") for item in tank_outbounds}
    main_options = [tag for tag in main_options if tag in existing_tags]
    if not main_options:
        return False

    selector: Dict[str, Any] = {
        "type": "selector",
        "tag": "🌍 Proxy Select",
        "outbounds": main_options,
    }
    if "🚀 Auto" in main_options:
        selector["default"] = "🚀 Auto"
    tank_outbounds.append(selector)
    return True


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
        chain_outbounds = chain_outbounds_from_details(p.details or {})
        if chain_outbounds:
            continue  # chains handled separately
        sb_proxy = to_singbox_outbound(p)
        if sb_proxy:
            tag = p.remarks or f"{p.protocol}-{p.id[:8]}"
            sb_proxy["tag"] = tag
            _base_outbound_cache[p.id] = (tag, sb_proxy)

    # Sniper (Standard singbox.json) - Smart Routing + TLS Fragmentation
    outbounds: List[Dict[str, Any]] = []
    selector_tags: List[str] = []
    seen_tags: Set[str] = set()
    tag_remap: Dict[str, str] = {}

    for p in proxies:
        if _is_washed_proxy(p, washed_ids):
            continue

        chain_outbounds = chain_outbounds_from_details(p.details or {})
        if chain_outbounds:
            _append_chain_uniquified(
                chain_outbounds, outbounds, seen_tags, tag_remap, selector_tags
            )
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
                enable_multiplexing=True,
                enable_tfo=True,
                enable_mptcp=True,
            )
        elif evasion_mode == "stealth":
            sb_proxy = enrich_outbound_with_evasion(
                sb_proxy,
                p.id,
                enable_utls=True,
                enable_alpn=False,
                enable_multiplexing=False,
                enable_tfo=True,
                enable_mptcp=False,
            )
        else:  # standard - no evasion (compatibility mode)
            sb_proxy = enrich_outbound_with_evasion(
                sb_proxy,
                p.id,
                enable_utls=False,
                enable_alpn=False,
                enable_multiplexing=False,
                enable_tfo=False,
                enable_mptcp=False,
            )
        # Mark evasion features based on actual mode, not unconditionally True
        if not p.details:
            p.details = {}
        p.details["has_utls"] = evasion_mode in ("aggressive", "stealth")
        # Native sing-box no longer exposes TLS fragmentation dial fields.
        p.details["has_fragmentation"] = False
        p.details["has_multiplexing"] = evasion_mode == "aggressive"
        p.details["has_alpn_rotation"] = evasion_mode == "aggressive"
        p.details["has_tfo"] = evasion_mode in ("aggressive", "stealth")
        p.details["has_mptcp"] = evasion_mode == "aggressive"
        # sing-box supports padding on the multiplex object, not on TLS.
        p.details["has_padding"] = evasion_mode == "aggressive"
        if tag and tag in seen_tags:
            tag_suffix = 0
            while f"{tag}-{tag_suffix}" in seen_tags:
                tag_suffix += 1
            tag = f"{tag}-{tag_suffix}"
            sb_proxy = copy.deepcopy(sb_proxy)
            sb_proxy["tag"] = tag
        outbounds.append(sb_proxy)
        if tag:
            seen_tags.add(tag)
            if tag not in selector_tags:
                selector_tags.append(tag)

    if washed_outbounds:
        _append_chain_uniquified(
            washed_outbounds,
            outbounds,
            seen_tags,
            tag_remap,
            selector_tags,
            add_all_non_relay=True,
        )

    # Ensure smart chains appear in singbox.json
    if smart_chains:
        for chain_list in smart_chains.values():
            for chain in chain_list:
                _append_chain_uniquified(
                    chain, outbounds, seen_tags, tag_remap, selector_tags
                )

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

    # Modern sing-box uses route actions for reject/DNS interception and
    # top-level endpoints for WireGuard. Emit that shape directly.
    if not any(o.get("tag") == "direct" for o in clean_outbounds):
        clean_outbounds.append({"type": "direct", "tag": "direct"})
    clean_outbounds, sniper_endpoints = _modernize_singbox_nodes(clean_outbounds)

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
    if sniper_endpoints:
        sniper_config["endpoints"] = sniper_endpoints
    if singbox_dns_profile:
        _attach_dns_profile(sniper_config, singbox_dns_profile, bool(selector_tags))

    sniper_path = output_dir / f"singbox{suffix}.json"
    AtomicFileWriter.write_text(
        sniper_path, json.dumps(sniper_config, indent=2, ensure_ascii=False)
    )
    files[f"singbox{key_suffix_str}"] = sniper_path

    # 2. Tank (singbox-vpn.json) - Full VPN/TUN - No Fragmentation (usually)
    tank_outbounds: List[Dict[str, Any]] = []
    tank_proxy_tags: List[str] = []
    tank_seen_tags: Set[str] = set()
    tank_tag_remap: Dict[str, str] = {}

    # Re-use cached base outbounds for Tank (clean slate, no evasion/frag)
    for p in proxies:
        if _is_washed_proxy(p, washed_ids):
            continue

        chain_outbounds = chain_outbounds_from_details(p.details or {})
        if chain_outbounds:
            _append_chain_uniquified(
                chain_outbounds,
                tank_outbounds,
                tank_seen_tags,
                tank_tag_remap,
                tank_proxy_tags,
            )
            continue

        cached = _base_outbound_cache.get(p.id)
        if not cached:
            continue
        tag, base_ob = cached
        if tag and tag in tank_seen_tags:
            tag_suffix = 0
            while f"{tag}-{tag_suffix}" in tank_seen_tags:
                tag_suffix += 1
            tag = f"{tag}-{tag_suffix}"
            base_ob = copy.deepcopy(base_ob)
            base_ob["tag"] = tag
        sb_proxy = copy.deepcopy(base_ob)
        tank_outbounds.append(sb_proxy)
        if tag:
            tank_seen_tags.add(tag)
            if tag not in tank_proxy_tags:
                tank_proxy_tags.append(tag)

    if washed_outbounds:
        _append_chain_uniquified(
            washed_outbounds,
            tank_outbounds,
            tank_seen_tags,
            tank_tag_remap,
            tank_proxy_tags,
            add_all_non_relay=True,
        )

    if smart_chains:
        for chain_list in smart_chains.values():
            for chain in chain_list:
                _append_chain_uniquified(
                    chain,
                    tank_outbounds,
                    tank_seen_tags,
                    tank_tag_remap,
                    tank_proxy_tags,
                )

    has_proxy_selector = _append_tank_groups(tank_outbounds, tank_proxy_tags)

    if not any(o.get("tag") == "direct" for o in tank_outbounds):
        tank_outbounds.append({"type": "direct", "tag": "direct"})

    # Strip internal metadata fields and modernize WireGuard before serializing.
    clean_tank_outbounds = _strip_internal_metadata(tank_outbounds)
    clean_tank_outbounds, tank_endpoints = _modernize_singbox_nodes(
        clean_tank_outbounds
    )

    tank_config: Dict[str, Any] = {
        "log": {"level": "info"},
        "inbounds": [
            {
                "type": "tun",
                "tag": "tun-in",
                "interface_name": "tun0",
                "address": ["172.19.0.1/30"],
                "auto_route": True,
                "strict_route": True,
            }
        ],
        "outbounds": clean_tank_outbounds,
        "route": {
            "rules": [
                {"protocol": "dns", "action": "hijack-dns"},
                {"clash_mode": "Direct", "outbound": "direct"},
                {
                    "clash_mode": "Global",
                    "outbound": "🌍 Proxy Select" if has_proxy_selector else "direct",
                },
            ]
        },
    }
    if tank_endpoints:
        tank_config["endpoints"] = tank_endpoints
    if singbox_dns_profile:
        _attach_dns_profile(tank_config, singbox_dns_profile, has_proxy_selector)

    tank_path = output_dir / f"singbox-vpn{suffix}.json"
    AtomicFileWriter.write_text(
        tank_path, json.dumps(tank_config, indent=2, ensure_ascii=False)
    )
    files[f"singbox_vpn{key_suffix_str}"] = tank_path

    # Clash
    clash_content = generate_clash_config(
        proxies, dns_profile=clash_dns_profile, ignore_status=True
    )
    if clash_content:
        clash_path = output_dir / f"clash{suffix}.yaml"
        AtomicFileWriter.write_text(clash_path, clash_content)
        files[f"clash{key_suffix_str}"] = clash_path

    return files
