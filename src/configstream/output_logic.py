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
            cc = p.country_code if p.country_code else "XX"
            by_country.setdefault(cc, []).append(p)
            by_protocol.setdefault(p.protocol, []).append(p)

    # Write Country files
    country_dir = output_dir / "countries"
    country_dir.mkdir(exist_ok=True)
    # Alias country_dir to by_country for tests
    by_country_dir = output_dir / "by_country"
    by_country_dir.mkdir(exist_ok=True)

    for cc, plist in by_country.items():
        # We generate files for all, including XX
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

    # [OPTIMIZATION] Single-pass loop to collect all stats at once (O(N) instead of O(4N))
    total = len(proxies)
    working = 0
    lat_dist = {"fast": 0, "medium": 0, "slow": 0, "very_slow": 0}
    protocols: Dict[str, int] = {}
    countries: Dict[str, int] = {}
    asns: Dict[str, int] = {}
    warp_count_heuristic = 0
    relay_count_heuristic = 0

    for p in proxies:
        if not p.is_working:
            continue

        working += 1

        # Latency distribution
        latency = p.latency or 9999
        if latency < 200:
            lat_dist["fast"] += 1
        elif latency < 800:
            lat_dist["medium"] += 1
        elif latency < 2000:
            lat_dist["slow"] += 1
        else:
            lat_dist["very_slow"] += 1

        # Protocol count
        protocols[p.protocol] = protocols.get(p.protocol, 0) + 1

        # Country count
        cc = p.country_code if p.country_code else "XX"
        countries[cc] = countries.get(cc, 0) + 1

        # ASN count
        if p.asn:
            asns[p.asn] = asns.get(p.asn, 0) + 1

        # Heuristic counts for WARP/RELAY tags
        tags_str = str(p.tags)
        if "WARP" in tags_str:
            warp_count_heuristic += 1
        if "RELAY" in tags_str:
            relay_count_heuristic += 1

    # Extract info from stats (dict or object)
    total_sourced = total
    parsed_count = total
    tested_count = total
    reasons = {}
    end_time_iso = datetime.now(timezone.utc).isoformat()
    washed_count = 0
    smart_chain_count = 0
    vwarp_win_rate = 0.0
    scanner_ips_found = 0
    fetched_sources = 0
    total_configured_sources = 0  # [FIX] Total sources from config for frontend display
    # [FIX] Additional stats that were missing from export
    revived_warp = 0
    revived_vwarp = 0
    vwarp_attempts = 0
    vwarp_success = 0
    duration_seconds = 0.0
    geo_resolved = 0
    cache_misses = 0
    final_count = 0

    if isinstance(stats, dict):
        # Stats is a dict (from merge script)
        total_sourced = stats.get("total_fetched", total)
        parsed_count = stats.get("parsed", total)
        tested_count = stats.get("tested", total)
        # reasons might be in stats['rejection_reasons'] if available, or empty
        reasons = stats.get("rejection_reasons", {})
        washed_count = stats.get("washed_chains", 0)
        smart_chain_count = 0
        if "smart_chains_breakdown" in stats:
            smart_chain_count = sum(stats["smart_chains_breakdown"].values())
        vwarp_win_rate = stats.get("vwarp_win_rate", 0.0)
        scanner_ips_found = stats.get("scanner_ips_found", 0)
        fetched_sources = stats.get("fetched_sources", 0)
        total_configured_sources = (
            stats.get("total_configured_sources", 0) or fetched_sources
        )
        # [FIX] Extract additional stats from dict
        revived_warp = stats.get("revived_warp", 0)
        revived_vwarp = stats.get("revived_vwarp", 0)
        vwarp_attempts = stats.get("vwarp_attempts", 0)
        vwarp_success = stats.get("vwarp_success", 0)
        duration_seconds = stats.get("duration", 0.0)
        geo_resolved = stats.get("geo_resolved", 0)
        cache_misses = stats.get("cache_misses", 0)
        final_count = stats.get("final_count", 0)
    else:
        # Stats is an object (PipelineStats)
        if hasattr(stats, "fetched_lines"):
            total_sourced = stats.fetched_lines
        elif hasattr(stats, "total_sourced"):
            total_sourced = stats.total_sourced
        if hasattr(stats, "parsed"):
            parsed_count = stats.parsed
        if hasattr(stats, "tested"):
            tested_count = stats.tested
        if hasattr(stats, "drop_reasons"):
            reasons = stats.drop_reasons
        if hasattr(stats, "end_time") and stats.end_time:
            end_time_iso = stats.end_time.isoformat()
        if hasattr(stats, "washer_success_count"):
            washed_count = stats.washer_success_count
        if hasattr(stats, "smart_chain_count"):
            smart_chain_count = stats.smart_chain_count
        if hasattr(stats, "vwarp_win_rate"):
            vwarp_win_rate = stats.vwarp_win_rate
        if hasattr(stats, "scanner_ips_found"):
            scanner_ips_found = stats.scanner_ips_found
        if hasattr(stats, "fetched_sources"):
            fetched_sources = stats.fetched_sources
        # [FIX] Extract total_configured_sources for frontend sources_count
        if hasattr(stats, "total_configured_sources"):
            total_configured_sources = stats.total_configured_sources or fetched_sources
        # [FIX] Extract additional stats from PipelineStats object
        if hasattr(stats, "revived_warp"):
            revived_warp = stats.revived_warp
        if hasattr(stats, "revived_vwarp"):
            revived_vwarp = stats.revived_vwarp
        if hasattr(stats, "vwarp_attempts"):
            vwarp_attempts = stats.vwarp_attempts
        if hasattr(stats, "vwarp_success"):
            vwarp_success = stats.vwarp_success
        if hasattr(stats, "duration"):
            duration_seconds = stats.duration
        if hasattr(stats, "geo_resolved"):
            geo_resolved = stats.geo_resolved
        if hasattr(stats, "cache_misses"):
            cache_misses = stats.cache_misses
        if hasattr(stats, "final_count"):
            final_count = stats.final_count

    # Fallback heuristics if counts still 0 (use values from single-pass loop)
    if washed_count == 0:
        washed_count = warp_count_heuristic
    if smart_chain_count == 0:
        smart_chain_count = relay_count_heuristic

    # Separation of Smart Chains
    smart_chains_breakdown = {}
    if isinstance(stats, dict) and "smart_chains_breakdown" in stats:
        smart_chains_breakdown = stats["smart_chains_breakdown"]

    try:
        pkg_version = version("configstream")
    except Exception:
        pkg_version = "unknown"

    # Calculate update interval (default 6 hours for production)
    update_interval_hours = int(os.getenv("UPDATE_INTERVAL_HOURS", "6"))

    # [FIX] Compute total_revived properly from both WARP and Vwarp
    total_revived_count = revived_warp + revived_vwarp
    if total_revived_count == 0:
        total_revived_count = washed_count  # Fallback to heuristic

    # Ensure total_revived is not zero if we have heuristics
    if total_revived_count == 0 and warp_count_heuristic > 0:
        total_revived_count = warp_count_heuristic

    meta = {
        "schema_version": "2.2.0",  # Bumped for new stats fields
        "version": pkg_version,
        "total_proxies": total,  # Total working proxies (final count)
        "total_tested": tested_count,  # Number of proxies actually tested
        "total_working": working,
        "success_rate": (working / tested_count) if tested_count > 0 else 0,
        "generated_at": end_time_iso,
        "last_updated_utc": end_time_iso,
        "latency_distribution": lat_dist,
        "protocols": protocols,
        "country_stats": countries,
        "rejection_reasons": reasons,
        "asns": asns,
        "isp_stats": asns,  # Alias for legacy tests
        "total_revived": total_revived_count,
        "total_smart_chains": smart_chain_count,
        "smart_chains_breakdown": smart_chains_breakdown,
        "total_dirty": reasons.get("dirty_ip", 0) + reasons.get("honeypot", 0),
        # Intelligence Layer Stats (canonical keys used by frontend)
        "vwarp_win_rate": vwarp_win_rate,
        "scanner_ips_found": scanner_ips_found,
        "washer_success_count": washed_count,
        "smart_chain_count": smart_chain_count,
        # [FIX] Export all revive/vwarp stats for complete tracking
        "revived_warp": revived_warp,
        "revived_vwarp": revived_vwarp,
        "vwarp_attempts": vwarp_attempts,
        "vwarp_success": vwarp_success,
        # [FIX] Export pipeline performance metrics
        "duration_seconds": duration_seconds,
        "geo_resolved": geo_resolved,
        "cache_misses": cache_misses,
        "final_count": final_count or working,
        # Canonical Keys (Consolidated)
        "total_lines_sourced": total_sourced,
        "total_unique_candidates": parsed_count,  # Parsed proxies (before testing)
        "total_valid_proxies": working,
        # Frontend display values - use total_configured_sources for proper display
        # [FIX] sources_count should show total configured sources, not just processed ones
        "sources_count": total_configured_sources or fetched_sources,
        "total_sources": total_configured_sources or fetched_sources,
        "fetched_sources": fetched_sources,  # Actual sources processed
        "update_interval_hours": update_interval_hours,
        # Legacy mappings for backward compatibility (tests only)
        "fetched_lines": total_sourced,
        "parsed": parsed_count,
        "tested": tested_count,
        "working": working,
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    # NOTE: statistics.json removed - metadata.json is now single source of truth
    # All frontend code updated to use metadata.json directly
