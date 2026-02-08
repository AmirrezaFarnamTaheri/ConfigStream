from typing import Dict, Any, List, Set
# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import asyncio
import ipaddress
from pathlib import Path
from typing import Optional

from configstream.models import Proxy
from configstream.history.tracker import ProxyHistoryTracker
from configstream.output_logic import (
    generate_categorized_outputs,
    save_metadata,
    _build_dns_safe_proxies,
    _build_dns_hardened_proxies,
)
from configstream.output_transport import save_json, inject_stego_key_into_frontend
from configstream.transport.stego import generate_stego_assets
from configstream.intelligence.washer.core import ProxyWasher
from configstream.intelligence.chaining import generate_smart_chains
from configstream.intelligence.vectors import generate_vectors
from configstream.pipeline_core.stats import PipelineStats
from configstream.tagging import ProxyTagger
from configstream.config import AppSettings
from configstream.dns_batch_resolver import BatchDNSResolver

logger = logging.getLogger(__name__)


def _normalize_host(value: str) -> str:
    return value.strip().lower().rstrip(".")


def _is_ip_literal(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


async def _populate_resolved_ips(
    proxies: List[Proxy], settings: AppSettings
) -> None:
    hostnames: List[str] = []
    for proxy in proxies:
        addr = (proxy.address or "").strip()
        if not addr or _is_ip_literal(addr):
            continue
        hostnames.append(addr)

    if not hostnames:
        return

    unique_hosts = list(dict.fromkeys(hostnames))
    limit = int(getattr(settings, "DNS_SAFE_RESOLVE_LIMIT", 0) or 0)
    if limit > 0:
        unique_hosts = unique_hosts[:limit]

    resolver = BatchDNSResolver(timeout=float(getattr(settings, "DNS_SAFE_RESOLVE_TIMEOUT", 4.0)))
    if resolver.resolver is None:
        logger.debug("DNS-safe outputs: batch resolver unavailable; skipping DNS resolution.")
        return

    batch_size = int(getattr(settings, "DNS_SAFE_RESOLVE_BATCH", 500) or 500)
    resolved: dict[str, str] = {}
    for i in range(0, len(unique_hosts), batch_size):
        batch = unique_hosts[i : i + batch_size]
        batch_resolved = await resolver.resolve(batch)
        for host, ip_value in batch_resolved.items():
            resolved[_normalize_host(host)] = ip_value

    if not resolved:
        logger.info("DNS-safe outputs: no hostnames resolved.")
        return

    for proxy in proxies:
        addr = (proxy.address or "").strip()
        if not addr:
            continue
        key = _normalize_host(addr)
        if key in resolved:
            proxy.resolved_ip = resolved[key]

    logger.info(
        "DNS-safe outputs: resolved %d of %d unique hostnames.",
        len(resolved),
        len(unique_hosts),
    )


async def generate_pipeline_outputs(
    optimized_proxies: List[Proxy],
    output_path: Path,
    stats: PipelineStats,
    history: ProxyHistoryTracker,
    washer: Optional[ProxyWasher] = None,
):
    """
    Orchestrates the generation of all pipeline outputs.
    Integrates Tagging, Washing, Smart Chaining, and File Generation.
    """
    logger.info("Starting final output generation phase...")

    # 0. Apply Tagging Strategy (Name formatting)
    # This applies user-defined or default naming templates to proxy remarks.
    # Must run BEFORE output generation so converters can use the formatted names.
    settings = AppSettings()
    rename_template = settings.RENAME_TEMPLATE
    tagger = ProxyTagger(rename_template)
    logger.info(f"Applying proxy tagging with template: {tagger.template}")
    tagger.apply(optimized_proxies)

    # 0b. DNS-safe resolution (optional)
    if getattr(settings, "DNS_SAFE_OUTPUTS", True):
        await _populate_resolved_ips(optimized_proxies, settings)
        # Track DNS-safe count
        dns_safe_proxies, _ = _build_dns_safe_proxies(optimized_proxies)
        stats.evasion_dns_safe_count = len(dns_safe_proxies)
    
    # Track DNS-hardened count
    if getattr(settings, "DNS_HARDENED_OUTPUTS", True):
        dns_hardened_proxies, _ = _build_dns_hardened_proxies(optimized_proxies)
        stats.evasion_dns_hardened_count = len(dns_hardened_proxies)

    # 1. Initialize Washer & Scanner (The Intelligence Layer)
    # We load keys from Env. If empty, washer degrades gracefully to no-op.
    if washer is None:
        washer = ProxyWasher(AppSettings().WARP_KEY_POOL)
        # Run the Go Scanner (Phase 2 Component)
        # This populates self.clean_ips in the washer with fresh, low-latency endpoints.
        # We await it because it's an async network operation.
        await washer.fetch_clean_ips()

    # Update stats with scanner results
    stats.scanner_ips_found = len(washer.clean_ips)

    # 2. Wash Batch (The "Blanket" Wash)
    # Generates standard WARP wraps for all working proxies (fallback/legacy behavior)
    # Returns the list of outbound configs and the set of IDs that were washed.
    # Pass stats object for metrics instrumentation
    washed_outbounds, washed_ids, skip_reasons = washer.wash_batch(
        optimized_proxies, stats=stats
    )

    # Update stats with washing results
    stats.washer_success_count = len(washed_ids)

    # 2b. The "Lazarus Pit" - Resurrect dead proxies with Shielding
    # Capture failed proxies and attempt to shield them (Copper to Gold transformation)
    failed_proxies = [p for p in optimized_proxies if not p.is_working]
    shielded_outbounds: List[Dict[str, Any]] = []
    shielded_ids: Set[str] = set()
    
    if failed_proxies and washer:
        logger.info(f"⚰️  Attempting to resurrect {len(failed_proxies)} dead proxies with Alchemy...")
        try:
            shielded_outbounds, shielded_ids = washer.shield_batch(failed_proxies, stats=stats)
            if shielded_outbounds:
                logger.info(f"✨  Alchemy Success! Resurrected {len(shielded_outbounds)//2} chains.")
                # Merge shielded outbounds with washed outbounds
                washed_outbounds.extend(shielded_outbounds)
                washed_ids.update(shielded_ids)
                stats.shielded_count = len(shielded_ids)
            else:
                logger.info("No dead proxies could be resurrected (no WARP keys or clean IPs available).")
        except Exception as e:
            logger.warning(f"Shielding failed: {e}", exc_info=True)
    
    # Track evasion metrics (count proxies with evasion features enabled)
    # Note: These are applied in generate_split_outputs, so we estimate based on working proxies
    working_with_tls = [p for p in optimized_proxies if p.is_working and p.protocol in ["vmess", "vless", "trojan", "hysteria2", "tuic"]]
    stats.evasion_utls_enabled = len(working_with_tls)  # All TLS proxies get uTLS
    stats.evasion_alpn_enabled = len([p for p in working_with_tls if p.protocol in ["vmess", "vless", "trojan"]])  # ALPN for specific protocols
    stats.evasion_fragmentation_enabled = len(working_with_tls)  # All TLS proxies get fragmentation
    stats.evasion_multiplexing_enabled = len([p for p in working_with_tls if p.protocol in ["vmess", "vless", "trojan", "shadowsocks"]])  # Multiplexing for specific protocols

    # [FIX] Explicit logging if no chains were created despite having working proxies
    if not washed_outbounds and optimized_proxies:
        logger.info(
            "WARP wrap skipped for all proxies (no valid WARP endpoints or keys found)."
        )

    # 3. Smart Chains (The Topology Router)
    # Generates complex chains (Intranet, IPv6, Streamer).
    # We pass the 'washer' instance so it can borrow the Clean IPs and Keys
    # to create "Washed Smart Chains" (3-hop).
    smart_chains = {}
    if settings.ENABLE_SMART_CHAINING:
        smart_chains = generate_smart_chains(optimized_proxies, washer=washer)
    else:
        logger.info("Smart chaining disabled by configuration.")

    # Update stats with smart chain counts (total number of chains generated)
    total_chains = sum(len(v) for v in smart_chains.values())
    stats.smart_chain_count = total_chains

    # 4. Generate Files (The Assembler)
    # Writes everything to disk: Sing-box (with chains), Clash (raw), Subs, etc.

    # Generate Master Proxies JSON with Rotation
    proxies_path = output_path / "proxies.json"
    old_proxies_path = output_path / "proxies.old.json"

    if proxies_path.exists():
        try:
            # Perform rotation for differential updates
            import shutil

            shutil.copy2(proxies_path, old_proxies_path)
            logger.info("Rotated proxies.json -> proxies.old.json for diff generation")
        except Exception as e:
            logger.warning(f"Failed to rotate proxies.json: {e}")

    # Run blocking file I/O in executor
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, save_json, optimized_proxies, proxies_path)

    # DNS-safe dataset (IP-only)
    dns_safe_proxies, _ = _build_dns_safe_proxies(optimized_proxies)
    dns_safe_path: Optional[Path] = None
    if dns_safe_proxies:
        dns_safe_path = output_path / "proxies-dns-safe.json"
        await loop.run_in_executor(None, save_json, dns_safe_proxies, dns_safe_path)

    # DNS-hardened dataset (prefer IP when available)
    dns_hardened_proxies, _ = _build_dns_hardened_proxies(optimized_proxies)
    dns_hardened_path: Optional[Path] = None
    if dns_hardened_proxies:
        dns_hardened_path = output_path / "proxies-dns-hardened.json"
        await loop.run_in_executor(
            None, save_json, dns_hardened_proxies, dns_hardened_path
        )

    revived_proxies = [
        p
        for p in optimized_proxies
        if (p.process or "").startswith("revived") or p.details.get("is_revived")
    ]
    revived_path = None
    revived_dns_path: Optional[Path] = None
    revived_hardened_path: Optional[Path] = None
    if revived_proxies:
        revived_path = output_path / "revived.json"
        await loop.run_in_executor(None, save_json, revived_proxies, revived_path)
        if dns_safe_proxies:
            revived_dns_safe = [
                p
                for p in dns_safe_proxies
                if (p.process or "").startswith("revived") or p.details.get("is_revived")
            ]
            if revived_dns_safe:
                revived_dns_path = output_path / "revived-dns-safe.json"
                await loop.run_in_executor(
                    None, save_json, revived_dns_safe, revived_dns_path
                )
        if dns_hardened_proxies:
            revived_dns_hardened = [
                p
                for p in dns_hardened_proxies
                if (p.process or "").startswith("revived") or p.details.get("is_revived")
            ]
            if revived_dns_hardened:
                revived_hardened_path = output_path / "revived-dns-hardened.json"
                await loop.run_in_executor(
                    None, save_json, revived_dns_hardened, revived_hardened_path
                )
    else:
        # [FIX] Log if no revived proxies found, for debugging
        logger.info(
            "No revived proxies found to export (revived.json will not be created)."
        )

    generated_files = await loop.run_in_executor(
        None,
        lambda: generate_categorized_outputs(
            optimized_proxies,
            output_path,
            washed_outbounds=washed_outbounds,
            washed_ids=washed_ids,
            smart_chains=smart_chains,
            washer=washer,
        ),
    )
    if revived_path:
        generated_files["revived"] = revived_path
    if dns_safe_path:
        generated_files["proxies_dns_safe"] = dns_safe_path
    if dns_hardened_path:
        generated_files["proxies_dns_hardened"] = dns_hardened_path
    if revived_dns_path:
        generated_files["revived_dns_safe"] = revived_dns_path
    if revived_hardened_path:
        generated_files["revived_dns_hardened"] = revived_hardened_path

    # 5. Metadata & Stats
    # Track total unique chain outbounds (revived + washed + smart chains)
    chain_outbounds: List[dict] = []
    seen_tags: set[str] = set()

    def _append_chain(outbounds: List[dict]) -> None:
        for outbound in outbounds:
            if not isinstance(outbound, dict):
                continue
            tag = outbound.get("tag")
            if tag and tag in seen_tags:
                continue
            chain_outbounds.append(outbound)
            if tag:
                seen_tags.add(tag)

    for proxy in optimized_proxies:
        chain = proxy.details.get("chain_outbounds")
        if isinstance(chain, list) and chain:
            _append_chain(chain)

    if washed_outbounds:
        _append_chain(washed_outbounds)

    if smart_chains:
        for chain_list in smart_chains.values():
            for chain in chain_list:
                if isinstance(chain, list) and chain:
                    _append_chain(chain)

    stats.chain_outbounds_count = len(chain_outbounds)

    stats_dict = stats.to_dict()

    await loop.run_in_executor(
        None, save_metadata, stats_dict, optimized_proxies, output_path
    )

    # 5b. Vector map for frontend similarity search
    await loop.run_in_executor(None, generate_vectors, optimized_proxies, output_path)

    # 6. Stego Assets + Frontend Key Injection (optional)
    secret_key = settings.STEGO_KEY or settings.CONFIG_STREAM_KEY
    if isinstance(secret_key, str) and secret_key.strip() and len(secret_key) >= 20:
        frontend_root = (
            Path(settings.FRONTEND_DIR)
            if settings.FRONTEND_DIR
            else Path(__file__).resolve().parents[3] / "frontend"
        )
        if frontend_root.exists():
            assets_dir = frontend_root / "assets" / "images"
            stego_js_path = frontend_root / "assets" / "js" / "stego.js"
            await loop.run_in_executor(
                None, generate_stego_assets, output_path, assets_dir, secret_key
            )
            await loop.run_in_executor(
                None,
                inject_stego_key_into_frontend,
                secret_key,
                stego_js_path,
            )
        else:
            logger.debug(
                "Frontend directory not found; skipping stego asset generation."
            )
    else:
        logger.debug("Stego generation skipped: STEGO_KEY not configured.")

    # Export history visualization data
    # Ensure the history visualization JSON is generated for the frontend
    viz_path = output_path / "data" / "proxy_history_viz.json"
    viz_path.parent.mkdir(parents=True, exist_ok=True)
    await loop.run_in_executor(None, history.export_for_visualization, viz_path)

    # Also export active trend for analytics chart
    trend_path = output_path / "data" / "active_proxy_trend.json"
    await loop.run_in_executor(None, history.export_active_proxy_trend, trend_path)

    # Export evasion trend for time-series charts
    evasion_trend_path = output_path / "data" / "evasion_trend.json"
    await loop.run_in_executor(None, history.export_evasion_trend, stats, evasion_trend_path)

    logger.info(f"Output generation complete. Files created in {output_path}")
    return generated_files
