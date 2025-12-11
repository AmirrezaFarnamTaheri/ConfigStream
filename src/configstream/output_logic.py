import os
import json
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime, timezone
from importlib.metadata import version

from .models import Proxy
from .output_generators import (
    generate_singbox_config,
    generate_base64_subscription,
    generate_split_outputs,
)
from .intelligence.chaining import generate_smart_chains
from .intelligence.washer.core import ProxyWasher

logger = logging.getLogger(__name__)


def generate_categorized_outputs(
    proxies: List[Proxy],
    output_dir: Path,
    washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    washed_ids: Optional[set] = None,
    smart_chains: Optional[Dict[str, List[List[Dict[str, Any]]]]] = None,
    washer: Optional[ProxyWasher] = None,  # Pass existing washer instance
) -> Dict[str, Path]:
    """
    Generates all output files categorized by protocol, country, and type.
    Now includes Smart Chains and Washed Proxies.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files = {}

    # Initialize washer if not provided (fallback)
    if washer is None:
        washer = ProxyWasher(os.getenv("WARP_KEY_POOL", "[]"))

    # 1. Generate Smart Chains if not provided
    if smart_chains is None:
        smart_chains = generate_smart_chains(proxies, washer=washer)

    # 2. Generate Split Outputs (The Tank & The Sniper & Clash)
    # This restores singbox-vpn.json (Tank) and singbox.json (Sniper)
    split_files = generate_split_outputs(
        proxies,
        output_dir,
        washed_outbounds=washed_outbounds,
        washed_ids=washed_ids,
        smart_chains=smart_chains,
    )
    generated_files.update(split_files)

    # Map for legacy tests/expectations
    if "singbox" in split_files:
        generated_files["singbox_full"] = split_files["singbox"]
        # Legacy test might expect "master" key?
        generated_files["master"] = split_files["singbox"]
    if "singbox_vpn" in split_files:
        generated_files["singbox_vpn"] = split_files["singbox_vpn"]
    if "clash" in split_files:
        generated_files["clash_full"] = split_files["clash"]

    # 3. Standard Subscription (Base64)
    sub_path = output_dir / "sub.txt"
    sub_content = generate_base64_subscription(proxies)
    with open(sub_path, "w", encoding="utf-8") as f:
        f.write(sub_content)
    generated_files["sub_full"] = sub_path

    # 4. Categorized Sub-files (By Country & Protocol)
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
    # Alias country_dir to by_country for tests
    by_country_dir = output_dir / "by_country"
    by_country_dir.mkdir(exist_ok=True)

    for cc, plist in by_country.items():
        if not cc or cc == "XX":
            continue
        cpath = country_dir / f"{cc}.json"
        with open(cpath, "w", encoding="utf-8") as f:
            f.write(generate_singbox_config(plist))

        # Write to by_country as well for tests
        bcpath = by_country_dir / f"{cc}.json"
        with open(bcpath, "w", encoding="utf-8") as f:
            f.write(generate_singbox_config(plist))
        generated_files[f"country_{cc}"] = bcpath

    # Write Protocol files
    proto_dir = output_dir / "protocols"
    proto_dir.mkdir(exist_ok=True)
    # Alias to by_protocol for tests
    by_proto_dir = output_dir / "by_protocol"
    by_proto_dir.mkdir(exist_ok=True)

    for proto, plist in by_protocol.items():
        ppath = proto_dir / f"{proto}.json"
        with open(ppath, "w", encoding="utf-8") as f:
            f.write(generate_singbox_config(plist))

        bppath = by_proto_dir / f"{proto}.json"
        with open(bppath, "w", encoding="utf-8") as f:
            f.write(generate_singbox_config(plist))
        generated_files[f"proto_{proto}"] = bppath

    logger.info(f"Generated {len(generated_files)} output files.")
    return generated_files


def save_metadata(
    stats: Any,
    proxies: List[Proxy],
    output_dir: Path,
):
    """
    Saves metadata.json and other stats files.
    """
    meta_path = output_dir / "metadata.json"

    # Calculate simple stats
    total = len(proxies)
    working = sum(1 for p in proxies if p.is_working)

    # Calculate Latency Distribution
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

    # Extract info from stats (dict or object)
    total_sourced = total
    reasons = {}
    end_time_iso = datetime.now(timezone.utc).isoformat()
    washed_count = 0
    smart_chain_count = 0

    if isinstance(stats, dict):
        # Stats is a dict (from merge script)
        total_sourced = stats.get("total_fetched", total)
        # reasons might be in stats['rejection_reasons'] if available, or empty
        reasons = stats.get("rejection_reasons", {})
        washed_count = stats.get("washed_chains", 0)
        smart_chain_count = 0
        if "smart_chains_breakdown" in stats:
            smart_chain_count = sum(stats["smart_chains_breakdown"].values())
    else:
        # Stats is an object (PipelineStats)
        if hasattr(stats, "fetched_lines"):
            total_sourced = stats.fetched_lines
        elif hasattr(stats, "total_sourced"):
            total_sourced = stats.total_sourced
        if hasattr(stats, "drop_reasons"):
            reasons = stats.drop_reasons
        if hasattr(stats, "end_time") and stats.end_time:
            end_time_iso = stats.end_time.isoformat()
        if hasattr(stats, "washer_success_count"):
            washed_count = stats.washer_success_count
        if hasattr(stats, "smart_chain_count"):
            smart_chain_count = stats.smart_chain_count

    # Fallback heuristics if counts still 0
    if washed_count == 0:
        washed_count = sum(1 for p in proxies if p.is_working and "WARP" in str(p.tags))
    if smart_chain_count == 0:
        smart_chain_count = sum(
            1 for p in proxies if p.is_working and "RELAY" in str(p.tags)
        )

    # Separation of Smart Chains
    smart_chains_breakdown = {}
    if isinstance(stats, dict) and "smart_chains_breakdown" in stats:
        smart_chains_breakdown = stats["smart_chains_breakdown"]

    # ASNs
    asns: Dict[str, int] = {}
    for p in proxies:
        if p.is_working and p.asn:
            asns[p.asn] = asns.get(p.asn, 0) + 1

    try:
        pkg_version = version("configstream")
    except Exception:
        pkg_version = "unknown"

    meta = {
        "version": pkg_version,
        "total_proxies": total,  # Changed to reflect actual proxies (parsed), not lines
        "total_tested": total,
        "total_working": working,
        "success_rate": (working / total) if total > 0 else 0,
        "generated_at": end_time_iso,
        "last_updated_utc": end_time_iso,
        "latency_distribution": lat_dist,
        "protocols": protocols,
        "country_stats": countries,
        "rejection_reasons": reasons,
        "asns": asns,
        "isp_stats": asns,  # Alias for legacy tests
        "total_revived": washed_count,
        "total_smart_chains": smart_chain_count,
        "smart_chains_breakdown": smart_chains_breakdown,
        "total_dirty": reasons.get("dirty_ip", 0) + reasons.get("honeypot", 0),
        # Canonical Keys (Consolidated)
        "total_lines_sourced": total_sourced,
        "total_unique_candidates": total,
        "total_valid_proxies": working,
        # Legacy mappings for backward compatibility
        "fetched_lines": total_sourced,
        "parsed": total,
        "tested": total,
        "working": working,
        "washed": washed_count,
        "smart_chains": smart_chain_count,
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
