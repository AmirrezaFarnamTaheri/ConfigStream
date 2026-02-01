# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import logging
import copy
import shutil
import os
import re
import tempfile
import zipfile
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime, timezone
from importlib.metadata import version

from .models import Proxy
from .converters.common import safe_int_conversion
from .output_generators import (
    generate_singbox_config,
    generate_base64_subscription,
    generate_split_outputs,
)
from .adapters import get_adapter
from .generators.plaintext import generate_plaintext_subscription
from .intelligence.chaining import generate_smart_chains
from .intelligence.washer.core import ProxyWasher
from .utils import AtomicFileWriter
from .config import AppSettings
from .constants import CHOSEN_TOP_PER_PROTOCOL, CHOSEN_TOTAL_TARGET

logger = logging.getLogger(__name__)


def _safe_filename(value: str, fallback: str) -> str:
    if not value:
        return fallback
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return clean or fallback


def _build_wireguard_config(proxy: Proxy) -> Optional[str]:
    details = proxy.details or {}
    private_key = details.get("private_key") or proxy.uuid or ""
    peer_public_key = details.get("peer_public_key") or details.get("public_key") or ""

    local_address = details.get("local_address") or details.get("private_ipv4")
    addresses: List[str] = []
    if isinstance(local_address, list):
        addresses = [str(item) for item in local_address if item]
    elif isinstance(local_address, str) and local_address:
        addresses = [local_address]

    if not private_key or not peer_public_key:
        return None

    allowed_ips = details.get("allowed_ips") or "0.0.0.0/0, ::/0"
    endpoint = f"{proxy.address}:{proxy.port}"
    keepalive = details.get("persistent_keepalive") or details.get("keepalive")
    dns = details.get("dns")

    lines = [
        "[Interface]",
        f"PrivateKey = {private_key}",
    ]
    if addresses:
        lines.append(f"Address = {', '.join(addresses)}")
    if dns:
        lines.append(f"DNS = {dns}")
    lines.append("")
    lines.extend(
        [
            "[Peer]",
            f"PublicKey = {peer_public_key}",
            f"AllowedIPs = {allowed_ips}",
            f"Endpoint = {endpoint}",
        ]
    )
    if keepalive:
        lines.append(f"PersistentKeepalive = {keepalive}")

    return "\n".join(lines) + "\n"


def _select_chosen_proxies(proxies: List[Proxy]) -> List[Proxy]:
    if CHOSEN_TOP_PER_PROTOCOL <= 0 and CHOSEN_TOTAL_TARGET <= 0:
        return []

    by_protocol: Dict[str, List[Proxy]] = {}
    for proxy in proxies:
        if not proxy.is_working:
            continue
        proto = (proxy.protocol or "unknown").lower()
        by_protocol.setdefault(proto, []).append(proxy)

    chosen: List[Proxy] = []
    for proto in sorted(by_protocol.keys()):
        candidates = sorted(
            by_protocol[proto],
            key=lambda p: (p.latency is None, p.latency or 9e9),
        )
        if CHOSEN_TOP_PER_PROTOCOL > 0:
            candidates = candidates[:CHOSEN_TOP_PER_PROTOCOL]
        chosen.extend(candidates)

    if CHOSEN_TOTAL_TARGET > 0 and len(chosen) > CHOSEN_TOTAL_TARGET:
        chosen = sorted(chosen, key=lambda p: (p.latency is None, p.latency or 9e9))[
            :CHOSEN_TOTAL_TARGET
        ]

    return chosen


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

    # Remove legacy redundant artifacts to keep output clean and canonical.
    legacy_files = ["raw.txt", "all.txt", "sub.txt", "vpn_subscription_base64.txt"]
    for name in legacy_files:
        legacy_path = output_dir / name
        if legacy_path.exists():
            try:
                legacy_path.unlink()
            except OSError:
                pass

    for legacy_dir in ("by_country", "by_protocol"):
        legacy_path = output_dir / legacy_dir
        if legacy_path.exists() and legacy_path.is_dir():
            try:
                shutil.rmtree(legacy_path)
            except OSError:
                pass

    # Initialize washer if not provided (fallback)
    if washer is None:
        washer = ProxyWasher(AppSettings().WARP_KEY_POOL)

    # 1. Generate Smart Chains if not provided
    if smart_chains is None:
        if AppSettings().ENABLE_SMART_CHAINING:
            smart_chains = generate_smart_chains(proxies, washer=washer)
        else:
            smart_chains = {}

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
    sub_content = generate_base64_subscription(proxies)
    base64_path = output_dir / "base64.txt"
    AtomicFileWriter.write_text(base64_path, sub_content)
    generated_files["base64"] = base64_path

    # 3b. Raw URI list (Plaintext) - single canonical file to avoid redundancy
    raw_content = generate_plaintext_subscription(proxies)
    proxies_txt_path = output_dir / "proxies.txt"
    AtomicFileWriter.write_text(proxies_txt_path, raw_content)
    generated_files["proxies_txt"] = proxies_txt_path

    # 3c. Chosen subset (top per protocol)
    chosen = _select_chosen_proxies(proxies)
    if chosen:
        chosen_dir = output_dir / "chosen"
        chosen_dir.mkdir(exist_ok=True)
        chosen_base64 = generate_base64_subscription(chosen)
        chosen_base64_path = chosen_dir / "base64.txt"
        AtomicFileWriter.write_text(chosen_base64_path, chosen_base64)
        generated_files["chosen_base64"] = chosen_base64_path

    # 3d. Adapter-specific outputs (Shadowrocket, QuantumultX, Surge, Loon, SIP008)
    adapter_specs = {
        "shadowrocket": ("shadowrocket", "shadowrocket.txt"),
        "quantumult": ("quantumultx", "quantumult.conf"),
        "surge": ("surge", "surge.conf"),
        "loon": ("loon", "loon.conf"),
        "sip008": ("sip008", "sip008.json"),
    }
    for key, (adapter_name, filename) in adapter_specs.items():
        try:
            adapter = get_adapter(adapter_name)
            if adapter_name in ("surge", "loon"):
                content = adapter.export(proxies, washed_outbounds=washed_outbounds)
            else:
                content = adapter.export(proxies)
            out_path = output_dir / filename
            AtomicFileWriter.write_text(out_path, content)
            generated_files[key] = out_path
        except Exception as exc:
            logger.warning("Failed to generate %s output: %s", adapter_name, str(exc))

    # 3e. Side products pack (OpenVPN + WireGuard + plain URIs)
    side_products_path = output_dir / "side_products.zip"
    openvpn_candidates = [
        p for p in proxies if (p.protocol or "").lower() == "openvpn" and p.config
    ]
    wireguard_candidates = [
        p for p in proxies if (p.protocol or "").lower() in ("wireguard", "wg")
    ]
    if raw_content or openvpn_candidates or wireguard_candidates:
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=output_dir, prefix=".side_products.", suffix=".tmp", delete=False
            ) as tmp:
                tmp_path = tmp.name
            with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("proxies.txt", raw_content)
                for proxy in openvpn_candidates:
                    name = _safe_filename(
                        proxy.remarks or proxy.id, f"openvpn-{proxy.id[:8]}"
                    )
                    zf.writestr(f"openvpn/{name}.ovpn", proxy.config)
                for proxy in wireguard_candidates:
                    wg_config = _build_wireguard_config(proxy)
                    if not wg_config:
                        continue
                    name = _safe_filename(
                        proxy.remarks or proxy.id, f"wireguard-{proxy.id[:8]}"
                    )
                    zf.writestr(f"wireguard/{name}.conf", wg_config)
            os.replace(tmp_path, side_products_path)
            generated_files["side_products"] = side_products_path
        except Exception as exc:
            logger.warning("Failed to generate side_products.zip: %s", str(exc))
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    # 4. Categorized Sub-files (By Country & Protocol)
    # Grouping
    by_country: Dict[str, List[Proxy]] = {}
    by_protocol: Dict[str, List[Proxy]] = {}

    for p in proxies:
        if p.is_working:
            cc = (p.country_code or "XX").upper()
            by_country.setdefault(cc, []).append(p)
            by_protocol.setdefault((p.protocol or "").lower(), []).append(p)

    # Write Country files
    country_dir = output_dir / "countries"
    country_dir.mkdir(exist_ok=True)

    for cc, plist in by_country.items():
        # We generate files for all, including XX
        cpath = country_dir / f"{cc}.json"
        AtomicFileWriter.write_text(cpath, generate_singbox_config(plist))

        generated_files[f"country_{cc}"] = cpath

    # Write Protocol files
    proto_dir = output_dir / "protocols"
    proto_dir.mkdir(exist_ok=True)

    for proto, plist in by_protocol.items():
        ppath = proto_dir / f"{proto}.json"
        AtomicFileWriter.write_text(ppath, generate_singbox_config(plist))

        generated_files[f"proto_{proto}"] = ppath

    # 5. Chain-only output (Washed + Revived + Smart Chains)
    chain_outbounds: List[Dict[str, Any]] = []
    seen_tags: set[str] = set()

    def _append_chain(outbounds: List[Dict[str, Any]]) -> None:
        for outbound in outbounds:
            if not isinstance(outbound, dict):
                continue
            tag = outbound.get("tag")
            if tag and tag in seen_tags:
                continue
            chain_outbounds.append(outbound)
            if tag:
                seen_tags.add(tag)

    for p in proxies:
        chain = p.details.get("chain_outbounds")
        if isinstance(chain, list) and chain:
            _append_chain(copy.deepcopy(chain))

    if washed_outbounds:
        _append_chain(copy.deepcopy(washed_outbounds))

    if smart_chains:
        for chain_list in smart_chains.values():
            for chain in chain_list:
                if isinstance(chain, list) and chain:
                    _append_chain(copy.deepcopy(chain))

    if chain_outbounds:
        chains_config_content = generate_singbox_config([], extra_outbounds=chain_outbounds)

        chains_path = output_dir / "singbox-chains.json"
        AtomicFileWriter.write_text(chains_path, chains_config_content)
        generated_files["singbox_chains"] = chains_path

        # [FIX] Alias: also save as chains.json if requested
        chains_alias_path = output_dir / "chains.json"
        AtomicFileWriter.write_text(chains_alias_path, chains_config_content)
        generated_files["chains"] = chains_alias_path

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

    # Single-pass loop to collect all stats at once (O(N) instead of O(4N))
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
    total_configured_sources = 0  # Total sources from config for frontend display
    # Additional stats that were missing from export
    revived_warp = 0
    revived_vwarp = 0
    vwarp_attempts = 0
    vwarp_success = 0
    duration_seconds = 0.0
    geo_resolved = 0
    cache_misses = 0
    final_count = 0
    time_limited = False
    time_limit_seconds = 0

    if isinstance(stats, dict):
        # Stats is a dict (from merge script)
        total_sourced = safe_int_conversion(
            stats.get("fetched_lines") or stats.get("total_fetched") or total
        )
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
        # Extract additional stats from dict
        revived_warp = stats.get("revived_warp", 0)
        revived_vwarp = stats.get("revived_vwarp", 0)
        vwarp_attempts = stats.get("vwarp_attempts", 0)
        vwarp_success = stats.get("vwarp_success", 0)
        duration_seconds = stats.get("duration", 0.0)
        geo_resolved = stats.get("geo_resolved", 0)
        cache_misses = stats.get("cache_misses", 0)
        final_count = stats.get("final_count", 0)
        time_limited = bool(stats.get("time_limited", False))
        time_limit_seconds = int(stats.get("time_limit_seconds", 0) or 0)
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
        # Extract total_configured_sources for frontend sources_count
        if hasattr(stats, "total_configured_sources"):
            total_configured_sources = stats.total_configured_sources or fetched_sources
        # Extract additional stats from PipelineStats object
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
        if hasattr(stats, "time_limited"):
            time_limited = bool(stats.time_limited)
        if hasattr(stats, "time_limit_seconds"):
            time_limit_seconds = int(stats.time_limit_seconds or 0)

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

    # Calculate update interval (default 5 hours for production)
    update_interval_hours = AppSettings().UPDATE_INTERVAL_HOURS

    # Compute total_revived properly from both WARP and Vwarp
    total_revived_count = revived_warp + revived_vwarp
    if total_revived_count == 0:
        total_revived_count = washed_count  # Fallback to heuristic

    # Ensure total_revived is not zero if we have heuristics
    if total_revived_count == 0 and warp_count_heuristic > 0:
        total_revived_count = warp_count_heuristic

    # Washing Enabled Logic (Best effort inference for Shards)
    washing_enabled = False
    warp_pool_raw = AppSettings().WARP_KEY_POOL
    if isinstance(warp_pool_raw, str) and warp_pool_raw.strip():
        try:
            warp_pool = json.loads(warp_pool_raw)
            washing_enabled = isinstance(warp_pool, list) and len(warp_pool) > 0
        except json.JSONDecodeError:
            # Non-JSON value treated as enabled if non-empty (backward compat)
            washing_enabled = True
    washing_enabled = washing_enabled or vwarp_attempts > 0

    meta = {
        "schema_version": "2.3.0",  # Updated to match generators.py
        "version": pkg_version,
        "total_proxies": total + smart_chain_count,  # Working proxies + smart chains
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
        # Export all revive/vwarp stats for complete tracking
        "revived_warp": revived_warp,
        "revived_vwarp": revived_vwarp,
        "vwarp_attempts": vwarp_attempts,
        "vwarp_success": vwarp_success,
        "washing_enabled": washing_enabled,
        # Export pipeline performance metrics
        "duration_seconds": duration_seconds,
        "geo_resolved": geo_resolved,
        "cache_misses": cache_misses,
        "final_count": final_count or working,
        "time_limited": time_limited,
        "time_limit_seconds": time_limit_seconds,
        # Canonical Keys (Consolidated)
        "total_lines_sourced": total_sourced,
        "total_unique_candidates": parsed_count,  # Parsed proxies (before testing)
        "total_valid_proxies": working,
        # Frontend display values - use total_configured_sources for proper display
        # sources_count should show total configured sources, not just processed ones
        "sources_count": total_configured_sources or fetched_sources,
        "total_sources": total_configured_sources or fetched_sources,
        "fetched_sources": fetched_sources,  # Actual sources processed
        "update_interval_hours": update_interval_hours,
        # Legacy mappings for backward compatibility (tests only)
        "fetched_lines": total_sourced,
        "parsed": parsed_count,
        "tested": tested_count,
        "working": working,
        # [FIX] Added chosen_subset_size for transparency
        "chosen_subset_size": len(_select_chosen_proxies(proxies)),
    }

    AtomicFileWriter.write_text(
        meta_path, json.dumps(meta, indent=2, ensure_ascii=False)
    )

    # NOTE: statistics.json removed - metadata.json is now single source of truth
    # All frontend code updated to use metadata.json directly
