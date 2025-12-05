import os
import json
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path

from .models import Proxy
from .output_generators import (
    generate_singbox_config,
    generate_clash_config,
    generate_subscription_file,
    generate_html_listing,
)
from .quality.storage import QualityStorage
from .intelligence.washer.chaining import generate_smart_chains
from .intelligence.washer.core import ProxyWasher

logger = logging.getLogger(__name__)


def generate_categorized_outputs(
    proxies: List[Proxy],
    output_dir: Path,
    washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    washed_ids: Optional[set] = None,
    smart_chains: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    washer: Optional[ProxyWasher] = None,  # Pass existing washer instance
) -> Dict[str, Path]:
    """
    Generates all output files categorized by protocol, country, and type.
    Now includes Smart Chains and Washed Proxies.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files = {}

    # Initialize washer if not provided (fallback)
    # But prioritize using the one passed in (which has clean IPs fetched)
    if washer is None:
        # Check if we have washed outbounds but no washer instance?
        # Ideally we create a fresh one if needed, but it won't have the Scan results.
        # This is just a fallback for standalone calls.
        washer = ProxyWasher(os.getenv("WARP_KEY_POOL", "[]"))

    # 1. Generate Smart Chains if not provided
    if smart_chains is None:
        # Use the washer instance for 3-hop chains
        smart_chains = generate_smart_chains(proxies, washer=washer)

    # 2. Main Sing-box Config (The Tank)
    # Includes standard proxies + Washed Proxies + Smart Chains
    extra_outbounds = []
    if washed_outbounds:
        extra_outbounds.extend(washed_outbounds)

    # Flatten smart chains into the extra_outbounds list
    if smart_chains:
        for chain_list in smart_chains.values():
            extra_outbounds.extend(chain_list)

    sb_path = output_dir / "singbox.json"
    sb_config = generate_singbox_config(proxies, extra_outbounds=extra_outbounds)
    with open(sb_path, "w", encoding="utf-8") as f:
        json.dump(sb_config, f, indent=2)
    generated_files["singbox_full"] = sb_path

    # 3. Clash Config (Legacy Support)
    # Note: Clash generator currently drops extra_outbounds as per audit
    clash_path = output_dir / "clash.yaml"
    clash_config = generate_clash_config(proxies)
    with open(clash_path, "w", encoding="utf-8") as f:
        f.write(clash_config)
    generated_files["clash_full"] = clash_path

    # 4. Standard Subscription (Base64)
    sub_path = output_dir / "sub.txt"
    sub_content = generate_subscription_file(proxies)
    with open(sub_path, "w", encoding="utf-8") as f:
        f.write(sub_content)
    generated_files["sub_full"] = sub_path

    # 5. Categorized Sub-files (By Country & Protocol)
    # Grouping
    by_country: Dict[str, List[Proxy]] = {}
    by_protocol: Dict[str, List[Proxy]] = {}

    for p in proxies:
        if p.is_working:
            by_country.setdefault(p.country_code, []).append(p)
            by_protocol.setdefault(p.protocol, []).append(p)

    # Write Country files
    country_dir = output_dir / "countries"
    country_dir.mkdir(exist_ok=True)
    for cc, plist in by_country.items():
        if not cc or cc == "XX":
            continue
        cpath = country_dir / f"{cc}.json"
        with open(cpath, "w", encoding="utf-8") as f:
            # Sing-box format for country slices
            json.dump(generate_singbox_config(plist), f, indent=2)

    # Write Protocol files
    proto_dir = output_dir / "protocols"
    proto_dir.mkdir(exist_ok=True)
    for proto, plist in by_protocol.items():
        ppath = proto_dir / f"{proto}.json"
        with open(ppath, "w", encoding="utf-8") as f:
            json.dump(generate_singbox_config(plist), f, indent=2)

    # 6. HTML Listing (for human verification)
    html_path = output_dir / "proxies.html"
    html_content = generate_html_listing(proxies)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    generated_files["html_listing"] = html_path

    logger.info(f"Generated {len(generated_files)} base output files + subcategories.")
    return generated_files


async def save_metadata(
    proxies: List[Proxy], output_dir: Path, stats: Any, history: QualityStorage
):
    """
    Saves metadata.json and other stats files.
    """
    meta_path = output_dir / "metadata.json"

    # Calculate simple stats
    total = len(proxies)
    working = sum(1 for p in proxies if p.is_working)

    # Calculate Latency Distribution
    # Group into: Fast (<200), Medium (200-800), Slow (800-2000), Very Slow (>2000)
    lat_dist = {"fast": 0, "medium": 0, "slow": 0, "very_slow": 0}
    for p in proxies:
        if p.is_working:
            latency = p.latency or 9999
            if latency < 200:
                lat_dist["fast"] += 1
            elif latency < 800:
                lat_dist["medium"] += 1
            elif latency < 2000:
                lat_dist["slow"] += 1
            else:
                lat_dist["very_slow"] += 1

    # Protocols
    protocols: Dict[str, int] = {}
    for p in proxies:
        if p.is_working:
            protocols[p.protocol] = protocols.get(p.protocol, 0) + 1

    # Countries
    countries: Dict[str, int] = {}
    for p in proxies:
        if p.is_working:
            countries[p.country_code] = countries.get(p.country_code, 0) + 1

    # Rejection Reasons (from stats object)
    # PipelineStats object accumulates reasons
    reasons = stats.drop_reasons if stats else {}

    # ASNs (if available in proxy details)
    asns: Dict[str, int] = {}
    for p in proxies:
        if p.is_working and p.asn:
            asns[p.asn] = asns.get(p.asn, 0) + 1

    # Washing Stats (Explicit from PipelineStats if available, else heuristic)
    if stats and hasattr(stats, "washer_success_count"):
        washed_count = stats.washer_success_count
    else:
        washed_count = sum(
            1 for p in proxies if p.is_working and "WARP" in str(p.tags)
        )  # Heuristic

    # Smart Chain Stats (Explicit from PipelineStats if available, else heuristic)
    if stats and hasattr(stats, "smart_chain_count"):
        smart_chain_count = stats.smart_chain_count
    else:
        smart_chain_count = sum(
            1 for p in proxies if p.is_working and "RELAY" in str(p.tags)
        )  # Heuristic

    meta = {
        "total_proxies": (
            stats.total_sourced if stats else total
        ),  # Total sourced from input
        "total_tested": total,  # Total passed to tester
        "total_working": working,
        "success_rate": (working / total) if total > 0 else 0,
        "generated_at": (
            stats.end_time.isoformat() if stats and stats.end_time else None
        ),
        "last_updated_utc": (
            stats.end_time.isoformat() if stats and stats.end_time else None
        ),
        "latency_distribution": lat_dist,
        "protocols": protocols,
        "country_stats": countries,
        "rejection_reasons": reasons,
        "asns": asns,
        # New Metrics
        "total_revived": washed_count,
        "total_smart_chains": smart_chain_count,
        # Threats (heuristic from rejection reasons)
        "total_dirty": reasons.get("dirty_ip", 0) + reasons.get("honeypot", 0),
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
