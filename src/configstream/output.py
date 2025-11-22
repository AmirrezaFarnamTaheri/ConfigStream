"""
Output Generation Module.
Produces client-compatible configuration files and statistical reports.
"""

import json
import gzip
import logging
import os
from pathlib import Path
from typing import List, Dict, Union, Optional, Any, Set
from datetime import datetime, timezone

from .models import Proxy
from .serialize import serialize_proxy
from .intelligence.washer import ProxyWasher, generate_smart_chains
from .utils import AtomicFileWriter
from .converters import to_singbox_outbound
from .output_generators import (
    generate_clash_config,
    generate_singbox_config,
    generate_base64_subscription,
)

logger = logging.getLogger(__name__)


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
    ipv6_tags = [o["tag"] for o in ipv6_exits]

    streamer_exits = [o for o in smart_chains["streamer"] if "EXIT" in o.get("tag", "")]
    streamer_tags = [o["tag"] for o in streamer_exits]

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
    with open(vpn_file, "w", encoding="utf-8") as f:
        json.dump(vpn_config, f, indent=2)
    files["singbox_vpn"] = vpn_file

    # 2. singbox.json (The "Sniper")
    sniper_config = {
        "log": {"level": "info"},
        "inbounds": [
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "127.0.0.1",
                "listen_port": 2080,
                "sniff": True,
            }
        ],
        "outbounds": [
            {
                "type": "selector",
                "tag": "🚀 Mode Selector",
                "outbounds": [
                    "⚡ Auto Fast",
                    "🛡️ Secure Washed",
                    "🇮🇷 Intranet Bridge",
                    "🇺🇸 US Streaming",
                    "🌌 IPv6 Portal",
                ],
            },
            {
                "type": "urltest",
                "tag": "⚡ Auto Fast",
                "outbounds": standard_tags,
                "url": "http://www.gstatic.com/generate_204",
                "interval": "5m",
            },
            {
                "type": "urltest",
                "tag": "🛡️ Secure Washed",
                "outbounds": washed_tags if washed_tags else ["direct"],
                "url": "http://www.gstatic.com/generate_204",
            },
            {
                "type": "urltest",
                "tag": "🇮🇷 Intranet Bridge",
                "outbounds": intranet_tags if intranet_tags else ["direct"],
                "url": "http://www.gstatic.com/generate_204",
            },
            {
                "type": "urltest",
                "tag": "🇺🇸 US Streaming",
                "outbounds": streamer_tags if streamer_tags else ["direct"],
                "url": "http://www.gstatic.com/generate_204",
            },
            {
                "type": "urltest",
                "tag": "🌌 IPv6 Portal",
                "outbounds": ipv6_tags if ipv6_tags else ["direct"],
                "url": "http://www.gstatic.com/generate_204",
            },
            {"type": "direct", "tag": "direct"},
            {"type": "dns", "tag": "dns-out"},
        ]
        + all_outbounds,
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
    with open(sniper_file, "w", encoding="utf-8") as f:
        json.dump(sniper_config, f, indent=2)
    files["singbox"] = sniper_file

    # 3. clash.yaml (The "Diplomat")
    clash_content = generate_clash_config(proxies)
    clash_file = output_dir / "clash.yaml"
    with open(clash_file, "w", encoding="utf-8") as f:
        f.write(clash_content)
    files["clash"] = clash_file

    return files


def generate_categorized_outputs(
    proxies: List[Proxy],
    output_dir: Path,
    washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    washed_ids: Optional[Set[str]] = None,
    smart_chains: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Path]:
    """
    Generate files organized by protocol and country.
    """
    files: Dict[str, Path] = {}

    # 1. Master List (Standard)
    master_file = output_dir / "proxies.json"
    save_json(proxies, master_file, compress=True)
    files["master"] = master_file

    # 1.1 Generate Advanced (Washed & Chained) Proxies
    # If not provided, generate them (backward compatibility / standalone use)
    if washed_outbounds is None or washed_ids is None:
        washer = ProxyWasher(os.getenv("WARP_KEY_POOL", "[]"))
        washed_outbounds, washed_ids = washer.wash_batch(proxies)

    if smart_chains is None:
        smart_chains = generate_smart_chains(proxies)

    # Save Chains separately (Sing-box only)
    chains_file = output_dir / "singbox-chains.json"
    all_chains = []
    for k, v in smart_chains.items():
        all_chains.extend(v)

    with open(chains_file, "w", encoding="utf-8") as f:
        chain_config = {"outbounds": all_chains}
        json.dump(chain_config, f, indent=2)
    files["chains"] = chains_file

    # 2. By Protocol
    proto_dir = output_dir / "by_protocol"
    proto_dir.mkdir(exist_ok=True)

    by_proto: Dict[str, List[Proxy]] = {}
    for p in proxies:
        proto = p.protocol.lower()
        if proto not in by_proto:
            by_proto[proto] = []
        by_proto[proto].append(p)

    for proto, subset in by_proto.items():
        fpath = proto_dir / f"{proto}.json"
        save_json(subset, fpath)
        files[f"proto_{proto}"] = fpath

    # 3. By Country
    country_dir = output_dir / "by_country"
    country_dir.mkdir(exist_ok=True)

    by_country: Dict[str, List[Proxy]] = {}
    for p in proxies:
        cc = (p.country_code or "UNK").upper()
        if cc not in by_country:
            by_country[cc] = []
        by_country[cc].append(p)

    for cc, subset in by_country.items():
        fpath = country_dir / f"{cc}.json"
        save_json(subset, fpath)
        files[f"country_{cc}"] = fpath

    # 4. Generate Split Outputs (Tank, Sniper, Diplomat)
    split_files = generate_split_outputs(
        proxies, output_dir, washed_outbounds, washed_ids, smart_chains
    )
    files.update(split_files)

    return files


def save_json(proxies: List[Proxy], path: Path, compress: bool = False) -> None:
    """
    Save list of proxies to JSON file atomically with fsync for durability.
    """
    data = [serialize_proxy(p) for p in proxies]
    json_content = json.dumps(data, indent=2, ensure_ascii=False)

    try:
        AtomicFileWriter.write_text(path, json_content)
    except Exception:
        raise

    if compress:
        gz_path = Path(str(path) + ".gz")
        try:
            temp_gz_path = gz_path.with_suffix(gz_path.suffix + ".tmp")
            try:
                with gzip.open(temp_gz_path, "wt", encoding="utf-8") as f:
                    f.write(json_content)
                os.replace(temp_gz_path, gz_path)
            except Exception:
                if temp_gz_path.exists():
                    temp_gz_path.unlink()
                raise
        except Exception:
            raise


def save_metadata(
    stats: Dict[str, Union[int, float]], proxies: List[Proxy], output_dir: Path
) -> None:
    """
    Save metadata.json with statistics for the frontend.
    """
    protocols: Dict[str, int] = {}
    countries: Dict[str, int] = {}
    country_stats: Dict[str, int] = {}
    latency_distribution = {"fast": 0, "medium": 0, "slow": 0, "very_slow": 0}

    for p in proxies:
        proto = p.protocol.lower()
        protocols[proto] = protocols.get(proto, 0) + 1
        cc = (p.country_code or "UNK").upper()
        countries[cc] = countries.get(cc, 0) + 1
        country_stats[cc] = country_stats.get(cc, 0) + 1

        latency = p.latency
        if latency is not None and latency > 0:
            if latency < 100:
                latency_distribution["fast"] += 1
            elif latency < 500:
                latency_distribution["medium"] += 1
            elif latency < 1000:
                latency_distribution["slow"] += 1
            else:
                latency_distribution["very_slow"] += 1
        else:
            latency_distribution["very_slow"] += 1

    total_working = int(stats.get("working", 0))
    fetched_lines = int(stats.get("fetched_lines", 0))
    duration = float(stats.get("duration", 0.0))

    metadata = {
        "last_updated_utc": datetime.now(timezone.utc).isoformat(),
        "total_proxies": len(proxies),
        "total_working": total_working,
        "total_fetched": fetched_lines,
        "duration_seconds": duration,
        "protocols": protocols,
        "countries": countries,
        "country_stats": country_stats,
        "latency_distribution": latency_distribution,
        "protocol_colors": {
            "vmess": "#FF6B6B",
            "vless": "#4ECDC4",
            "shadowsocks": "#45B7D1",
            "trojan": "#96CEB4",
            "hysteria": "#FFEAA7",
            "hysteria2": "#DFE6E9",
            "tuic": "#A29BFE",
            "wireguard": "#74B9FF",
            "naive": "#FD79A8",
            "http": "#FDCB6E",
            "https": "#6C5CE7",
            "socks": "#00B894",
            "socks5": "#00B894",
            "openvpn": "#E84393",
        },
    }

    metadata_content = json.dumps(metadata, indent=2)
    for filename in ["metadata.json", "summary.json"]:
        target_path = output_dir / filename
        try:
            AtomicFileWriter.write_text(target_path, metadata_content)
        except Exception:
            raise
