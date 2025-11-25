"""
Output Generators.
Refactored from output.py to reduce monolith size.
"""

import json
import base64
import logging
from typing import List, Dict, Any, Set
from pathlib import Path
from .models import Proxy
from .converters import to_clash_proxy, to_singbox_outbound
from .utils import AtomicFileWriter

logger = logging.getLogger(__name__)

try:
    import yaml as yaml_lib  # type: ignore[import-untyped]
except ImportError:
    logger.warning("PyYAML not found. Clash config generation will be disabled.")
    yaml_lib = None  # type: ignore


def generate_clash_config(proxies: List[Proxy]) -> str:
    """Generate Clash YAML configuration."""
    if yaml_lib is None:
        return "# PyYAML not installed"

    clash_proxies = []
    names = []

    for i, p in enumerate(proxies, 1):
        if not p.is_working:
            continue
        display_name = f"{p.country_code or 'XX'} {i:02d} | {p.protocol.upper()}"
        config = to_clash_proxy(p)
        if config:
            config["name"] = display_name
            clash_proxies.append(config)
            names.append(display_name)

    payload = {
        "port": 7890,
        "socks-port": 7891,
        "allow-lan": True,
        "mode": "Rule",
        "log-level": "info",
        "external-controller": "127.0.0.1:9090",
        "proxies": clash_proxies,
        "proxy-groups": [
            {
                "name": "🚀 ConfigStream Auto",
                "type": "url-test",
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
                "tolerance": 50,
                "proxies": names if names else ["DIRECT"],
            },
            {
                "name": "🌍 Proxy Select",
                "type": "select",
                "proxies": names + ["🚀 ConfigStream Auto"] if names else ["DIRECT"],
            },
        ],
        "rules": ["MATCH,🚀 ConfigStream Auto"],
    }

    result = yaml_lib.dump(payload, allow_unicode=True, sort_keys=False)
    return str(result) if result else ""


def generate_singbox_config(proxies: List[Proxy]) -> str:
    """Legacy method for backward compatibility."""
    outbounds: List[Dict[str, Any]] = []
    selector_tags: List[str] = []

    for i, p in enumerate(proxies, 1):
        config = to_singbox_outbound(p)
        if config:
            tag = f"{p.country_code or 'XX'} {i:02d} | {p.protocol.upper()}"
            config["tag"] = tag
            outbounds.append(config)
            selector_tags.append(tag)

    if selector_tags:
        outbounds.insert(
            0,
            {
                "type": "selector",
                "tag": "🌍 Proxy Select",
                "outbounds": ["🚀 Auto"] + selector_tags,
            },
        )
        outbounds.insert(
            1,
            {
                "type": "urltest",
                "tag": "🚀 Auto",
                "outbounds": selector_tags,
                "url": "http://www.gstatic.com/generate_204",
                "interval": "5m",
            },
        )

    full_config = {
        "log": {"level": "info"},
        "inbounds": [
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "127.0.0.1",
                "listen_port": 2080,
            }
        ],
        "outbounds": outbounds,
    }

    return json.dumps(full_config, indent=2)


def generate_base64_subscription(proxies: List[Proxy]) -> str:
    """Generate standard Base64 subscription string."""
    lines = []
    for p in proxies:
        if p.config and p.protocol != "openvpn" and "://" in p.config:
            lines.append(p.config)
    text = "\n".join(lines)
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")


def generate_split_outputs(
    proxies: List[Proxy],
    output_dir: Path,
    washed_outbounds: List[Dict[str, Any]],
    washed_ids: Set[str],
    smart_chains: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Path]:
    """
    Generate specific configuration files for different use cases.
    Includes washed proxies and smart chains in Sing-box configs.
    Filters out raw proxies that have been washed to avoid "Dirty Duplicates".
    """
    files: Dict[str, Path] = {}

    # Prepare selector lists
    standard_proxies = []
    standard_tags = []

    # Dirty Duplicate Filter:
    # If a proxy ID is in washed_ids, we do NOT add it to the standard (Auto) list.
    # It will be accessible via the "Washed" group.

    for i, p in enumerate(proxies, 1):
        if not p.is_working:
            continue

        # If proxy was washed, skip adding its raw/dirty version to main selectors
        if p.id in washed_ids:
            continue

        out = to_singbox_outbound(p)
        if out:
            tag = f"{p.country_code or 'XX'} {i:02d} | {p.protocol.upper()}"
            out["tag"] = tag
            standard_proxies.append(out)
            standard_tags.append(tag)

    # Washed Proxies (Tags starting with 🛡️ Secure)
    washed_exits = [
        o for o in washed_outbounds if o.get("tag", "").startswith("🛡️ Secure")
    ]
    washed_tags = [o["tag"] for o in washed_exits]

    # Smart Chain Exits
    intranet_exits = [o for o in smart_chains["intranet"] if "EXIT" in o.get("tag", "")]
    intranet_tags = [o["tag"] for o in intranet_exits]

    ipv6_exits = [o for o in smart_chains["ipv6"] if "EXIT" in o.get("tag", "")]
    ipv6_tags = [o["tag"] for o in ipv6_exits]  # noqa: F841

    streamer_exits = [o for o in smart_chains["streamer"] if "EXIT" in o.get("tag", "")]
    streamer_tags = [o["tag"] for o in streamer_exits]  # noqa: F841

    # Collect all outbounds for the config
    all_outbounds = standard_proxies + washed_outbounds
    for chain_list in smart_chains.values():
        all_outbounds.extend(chain_list)

    # 1. singbox-vpn.json (The "Tank")
    vpn_config = {
        "log": {"level": "info"},
        "dns": {
            "servers": [
                {"tag": "google", "address": "8.8.8.8", "detour": "🌍 Proxy Select"},
                {"tag": "local", "address": "223.5.5.5", "detour": "direct"},
            ],
            "rules": [{"outbound": "any", "server": "google"}],
            "final": "google",
            "strategy": "ipv4_only",
        },
        "inbounds": [
            {
                "type": "tun",
                "tag": "tun-in",
                "interface_name": "tun0",
                "inet4_address": "172.19.0.1/30",
                "auto_route": True,
                "strict_route": True,
                "stack": "gvisor",
                "sniff": True,
            }
        ],
        "outbounds": [
            {
                "type": "selector",
                "tag": "🌍 Proxy Select",
                "outbounds": ["🚀 Auto", "🛡️ Washed", "🇮🇷 Intranet"] + standard_tags,
            },
            {
                "type": "urltest",
                "tag": "🚀 Auto",
                "outbounds": standard_tags,
                "url": "http://www.gstatic.com/generate_204",
                "interval": "5m",
            },
            {
                "type": "selector",
                "tag": "🛡️ Washed",
                "outbounds": washed_tags if washed_tags else ["direct"],
            },
            {
                "type": "urltest",
                "tag": "🇮🇷 Intranet",
                "outbounds": intranet_tags if intranet_tags else ["direct"],
                "url": "http://www.gstatic.com/generate_204",
                "interval": "5m",
            },
            {"type": "direct", "tag": "direct"},
            {"type": "dns", "tag": "dns-out"},
        ]
        + all_outbounds,
    }

    vpn_file = output_dir / "singbox-vpn.json"
    AtomicFileWriter.write_text(vpn_file, json.dumps(vpn_config, indent=2))
    files["singbox_vpn"] = vpn_file

    # 2. singbox.json (The "Sniper" - Now "The Smart Sniper")

    # Define the Grouping Architecture

    # Group A: The Speed Demon (URL Test)
    # Aggressively checks every 5 mins. Switches to the fastest.
    auto_fast_group = {
        "type": "urltest",
        "tag": "⚡ Auto-Fast",
        "outbounds": standard_tags,  # The raw, fast proxies
        "url": "http://cp.cloudflare.com/generate_204",
        "interval": "5m",
        "tolerance": 50,  # Switch only if new proxy is >50ms faster
        "interrupt_exist_connections": False,
    }

    # Group B: The Unkillable (Fallback)
    # If Auto-Fast fails (all proxies dead), it falls back to Washed.
    # If Washed fails, it falls back to Intranet.
    fallback_group = {
        "type": "fallback",  # CRITICAL CHANGE: 'fallback' type
        "tag": "🛡️ Auto-Fallback",
        "outbounds": [
            "⚡ Auto-Fast",  # First try speed
            "🛡️ Secure Washed",  # Then try WARP chains
            "🇮🇷 Intranet Bridge",  # Last resort
        ],
        "url": "http://cp.cloudflare.com/generate_204",
        "interval": "5m",
    }

    # Group C: The Manual Override (Selector)
    # Allows user to pick a specific Country or Mode
    main_selector = {
        "type": "selector",
        "tag": "🚀 Mode Selector",
        "outbounds": [
            "🛡️ Auto-Fallback",  # Default: Smart Fallback
            "⚡ Auto-Fast",
            "🛡️ Secure Washed",
            "Manual Select",
            "direct",
        ],
    }

    # Group D: Country Buckets (Optional but good for UX)
    # You can generate these dynamically based on country codes if needed
    manual_select = {
        "type": "selector",
        "tag": "Manual Select",
        "outbounds": standard_tags,
    }

    # Assemble the Outbounds List
    final_outbounds = [
        main_selector,
        fallback_group,
        auto_fast_group,
        manual_select,
        # Add the referenced sub-groups
        {
            "type": "urltest",
            "tag": "🛡️ Secure Washed",
            "outbounds": washed_tags if washed_tags else ["direct"],
            "url": "http://cp.cloudflare.com/generate_204",
        },
        {
            "type": "urltest",
            "tag": "🇮🇷 Intranet Bridge",
            "outbounds": intranet_tags if intranet_tags else ["direct"],
            "url": "http://cp.cloudflare.com/generate_204",
        },
        {"type": "direct", "tag": "direct"},
        {"type": "dns", "tag": "dns-out"},
    ] + all_outbounds

    sniper_config = {
        "log": {"level": "info"},
        "dns": {
            # Standard DNS block provided in previous artifact or default
            "servers": [
                {"tag": "google", "address": "8.8.8.8", "detour": "🚀 Mode Selector"}
            ],
            "strategy": "ipv4_only",
        },
        "inbounds": [
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "127.0.0.1",
                "listen_port": 2080,
                "sniff": True,
            }
        ],
        "outbounds": final_outbounds,
    }

    # Inject fragmentation for Sniper
    for out in all_outbounds:
        # Be careful only to inject into TLS outbounds that are direct (not chains/selectors)
        # Actually we inject into the OUTBOUND definitions in the list
        if "tls" in out and isinstance(out["tls"], dict):
            out["tls"]["tls_fragment"] = {
                "enabled": True,
                "size": "100-200",
                "sleep": "10-20",
            }

    sniper_file = output_dir / "singbox.json"
    AtomicFileWriter.write_text(sniper_file, json.dumps(sniper_config, indent=2))
    files["singbox"] = sniper_file

    # 3. clash.yaml (The "Diplomat")
    clash_content = generate_clash_config(proxies)
    clash_file = output_dir / "clash.yaml"
    AtomicFileWriter.write_text(clash_file, clash_content)
    files["clash"] = clash_file

    return files
