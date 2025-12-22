import logging
import json
import copy
from pathlib import Path
from typing import List, Dict, Any, Set, Optional

from ..models import Proxy
from .clash import generate_clash_config
from ..converters import to_singbox_outbound

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


def generate_split_outputs(
    proxies: List[Proxy],
    output_dir: Path,
    washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    washed_ids: Optional[Set[str]] = None,
    smart_chains: Optional[Dict[str, List[List[Dict[str, Any]]]]] = None,
) -> Dict[str, Path]:
    """
    Generates split outputs (Tank/Sniper strategies) and Clash.
    """
    files: Dict[str, Path] = {}

    # 1. Sniper (Standard singbox.json) - Smart Routing + TLS Fragmentation
    outbounds = []
    selector_tags = []

    for p in proxies:
        # Skip washed proxies (they are replaced by washed_outbounds)
        if washed_ids and p.id in washed_ids:
            continue

        sb_proxy = to_singbox_outbound(p)
        if sb_proxy:
            tag = p.remarks or f"{p.protocol}-{p.id[:8]}"
            sb_proxy["tag"] = tag

            # Inject TLS Fragmentation (Sniper default)
            if "tls" in sb_proxy and isinstance(sb_proxy["tls"], dict):
                sb_proxy["tls"]["tls_fragment"] = {
                    "enabled": True,
                    "size": "100-200",
                    "sleep": "0-10",
                }
            outbounds.append(sb_proxy)
            selector_tags.append(tag)

    # Add washed outbounds
    if washed_outbounds:
        # Clone to avoid mutating shared objects
        washed_clones = copy.deepcopy(washed_outbounds)
        outbounds.extend(washed_clones)
        for w in washed_clones:
            if w.get("tag") and "RELAY" not in w["tag"]:
                selector_tags.append(w["tag"])

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
        # Add "⚡ Auto-Fast" alias for compatibility if needed
        outbounds.append(
            {
                "type": "selector",
                "tag": "⚡ Auto-Fast",
                "outbounds": ["🚀 Auto"],
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
                "outbounds": ["🚀 Auto", "⚡ Auto-Fast", "🛡️ Auto-Fallback"]
                + selector_tags,
                "default": "🚀 Auto",
            }
        )

    # [FIX] Strip internal metadata fields (like _process) before serializing
    # These fields cause Sing-box parse errors: "unknown field "_process""
    clean_outbounds = _strip_internal_metadata(outbounds)

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

    sniper_path = output_dir / "singbox.json"
    with open(sniper_path, "w") as f:
        json.dump(sniper_config, f, indent=2)
    files["singbox"] = sniper_path

    # 2. Tank (singbox-vpn.json) - Full VPN/TUN - No Fragmentation (usually)
    tank_outbounds = []
    tank_proxy_tags = []

    # Re-convert for Tank (clean slate, no frag)
    for p in proxies:
        if washed_ids and p.id in washed_ids:
            continue

        sb_proxy = to_singbox_outbound(p)
        if sb_proxy:
            tag = p.remarks or f"{p.protocol}-{p.id[:8]}"
            sb_proxy["tag"] = tag
            tank_outbounds.append(sb_proxy)
            tank_proxy_tags.append(tag)

    if washed_outbounds:
        tank_outbounds.extend(copy.deepcopy(washed_outbounds))

    if smart_chains:
        for chain_list in smart_chains.values():
            # Flatten chain list if needed, but it seems chain_list is List[List[Dict]]?
            # Actually, `generate_smart_chains` returns Dict[str, List[List[Dict]]].
            # So chain_list is List[List[Dict]]. We need to flatten it or iterate.
            for chain in chain_list:
                tank_outbounds.extend(copy.deepcopy(chain))

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
    # Check if "🚀 Auto" exists in outbounds tags
    existing_tags = set(o.get("tag") for o in tank_outbounds)
    main_options = [t for t in main_options if t in existing_tags]

    tank_outbounds.append(
        {
            "type": "selector",
            "tag": "🌍 Proxy Select",
            "outbounds": main_options,
            "default": "🚀 Auto" if "🚀 Auto" in main_options else None,
        }
    )

    if not any(o.get("tag") == "direct" for o in tank_outbounds):
        tank_outbounds.append({"type": "direct", "tag": "direct"})

    # [FIX] Strip internal metadata fields from tank outbounds too
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

    tank_path = output_dir / "singbox-vpn.json"
    with open(tank_path, "w") as f:
        json.dump(tank_config, f, indent=2)
    files["singbox_vpn"] = tank_path

    # Clash
    clash_content = generate_clash_config(proxies)
    if clash_content:
        clash_path = output_dir / "clash.yaml"
        with open(clash_path, "w") as f:
            f.write(clash_content)
        files["clash"] = clash_path

    return files
