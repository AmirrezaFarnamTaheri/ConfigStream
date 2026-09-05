# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Dict, Any, List, Optional, Set
import json
import logging
import asyncio
from pathlib import Path

from configstream.models import Proxy
from configstream.security_validator import SecurityValidator
from configstream.history.tracker import ProxyHistoryTracker
from configstream.output_logic import (
    generate_categorized_outputs,
    save_metadata,
    write_public_artifact_contract,
    _build_dns_safe_proxies,
    _build_dns_hardened_proxies,
)
from configstream.output_transport import save_json, inject_stego_key_into_frontend
from configstream.serialize import serialize_proxy, _build_chain_config
from configstream.stego import generate_stego_assets
from configstream.intelligence.washer.core import ProxyWasher
from configstream.intelligence.chaining import generate_smart_chains
from configstream.intelligence.vectors import generate_vectors
from configstream.converters.chain_outbounds import chain_obs_from_details
from configstream.pipeline_stats import PipelineStats
from configstream.tagging import ProxyTagger, format_proxy_name
from configstream.config import AppSettings
from configstream.dns_batch_resolver import BatchDNSResolver
from configstream.utils import AtomicFileWriter
from configstream.utils.net import (
    normalize_host as _normalize_host,
    is_ip_literal as _is_ip_literal,
)

# SingBoxTester is imported lazily inside generate_pipeline_outputs to avoid
# circular imports; the type hint uses TYPE_CHECKING to keep mypy happy.
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from configstream.testers.manager import SingBoxTester

logger = logging.getLogger(__name__)


def _rotate_proxy_snapshot(current: Path, previous: Path) -> None:
    try:
        content = current.read_bytes()
    except FileNotFoundError:
        return
    except OSError as exc:
        logger.warning(
            "Failed to read snapshot for rotation: %s",
            SecurityValidator.sanitize_log_message(str(exc)),
        )
        return
    try:
        AtomicFileWriter.write_bytes(previous, content)
    except OSError as exc:
        logger.warning(
            "Failed to rotate snapshot: %s",
            SecurityValidator.sanitize_log_message(str(exc)),
        )


def _log_geoip_enrichment_stats(proxies: List[Proxy]) -> Dict[str, int]:
    """Log enrichment coverage without constructing the optional GeoIP backend."""
    stats = {
        "total": len(proxies),
        "with_country": sum(
            1 for proxy in proxies if proxy.country_code and proxy.country_code != "XX"
        ),
        "with_city": sum(
            1 for proxy in proxies if proxy.city and proxy.city != "Unknown"
        ),
        "with_asn": sum(1 for proxy in proxies if proxy.asn),
    }
    coverage = stats["with_country"] / stats["total"] * 100 if stats["total"] else 0.0
    logger.info(
        "GeoIP enrichment: %d/%d (%.1f%%) countries resolved, %d cities, %d ASNs",
        stats["with_country"],
        stats["total"],
        coverage,
        stats["with_city"],
        stats["with_asn"],
    )
    return stats


def _is_revived(p: Proxy) -> bool:
    """Check if a proxy was revived via WARP/Vwarp."""
    details = p.details or {}
    flag = details.get("is_revived")
    is_revived_flag = False
    if isinstance(flag, bool):
        is_revived_flag = flag
    elif isinstance(flag, int):
        is_revived_flag = flag != 0
    elif isinstance(flag, str):
        is_revived_flag = flag.strip().lower() in ("1", "true", "yes", "y", "on")
    return (
        (p.process or "").startswith("revived")
        or (p.protocol or "") == "revived"
        or (p.config or "").startswith("revived://")
        or is_revived_flag
    )


def _is_clean_ip(host: str) -> bool:
    """Quick validation that a string looks like a real IPv4/IPv6 address."""
    host = host.strip()
    if not host:
        return False
    # IPv4: exactly 3 dots, all octets 0-255
    if host[0].isdigit() and host.count(".") == 3:
        return all(p.isdigit() and 0 <= int(p) <= 255 for p in host.split("."))
    # IPv6: at least 2 colons, only hex/colon/dot chars
    if host.count(":") >= 2 and all(c in "0123456789abcdefABCDEF:." for c in host):
        return True
    return False


def _save_clean_ips(clean_ips: List[tuple[str, int]], path: Path) -> None:
    """
    Save washer clean IPs for the frontend lab.
    Output shape matches frontend expectations: list of {ip, port}.
    """
    items: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for entry in clean_ips:
        try:
            ip, port = entry
        except Exception:  # nosec B112
            logging.getLogger(__name__).debug("Suppressed broad exception")
            continue
        ip_s = str(ip).strip()
        if not ip_s or not _is_clean_ip(ip_s):
            continue
        try:
            port_i = int(port)
        except Exception:
            logging.getLogger(__name__).debug("Suppressed broad exception")
            port_i = 2408
        key = f"{ip_s}:{port_i}"
        if key in seen:
            continue
        seen.add(key)
        items.append({"ip": ip_s, "port": port_i})
        if len(items) >= 200:
            break

    path.parent.mkdir(parents=True, exist_ok=True)
    AtomicFileWriter.write_text(path, json.dumps(items, indent=2, ensure_ascii=False))


def _group_chain_obs(
    outbounds: List[Dict[str, Any]],
) -> List[List[Dict[str, Any]]]:
    """Group flat outbound list into chains by following detour relationships."""
    if not outbounds:
        return []
    by_tag: Dict[str, Dict[str, Any]] = {
        ob["tag"]: ob for ob in outbounds if isinstance(ob, dict) and ob.get("tag")
    }
    detour_targets: set[str] = set()
    for ob in outbounds:
        dt = ob.get("detour")
        if isinstance(dt, str) and dt:
            detour_targets.add(dt)
    # Entry points: outbounds whose tag is NOT a detour target of someone else
    entry_points = [
        ob
        for ob in outbounds
        if isinstance(ob, dict) and ob.get("tag") and ob["tag"] not in detour_targets
    ]
    chains: List[List[Dict[str, Any]]] = []
    for entry in entry_points:
        chain: List[Dict[str, Any]] = []
        current: Optional[Dict[str, Any]] = entry
        visited: set[str] = set()
        while current:
            tag = current.get("tag", "")
            if tag in visited:
                break
            visited.add(tag)
            chain.append(current)
            dt = current.get("detour")
            current = by_tag.get(dt) if dt else None
        chain.reverse()  # inner hops first, entry point last
        chains.append(chain)
    return chains


def _chain_to_proxy_entry(
    chain: List[Dict[str, Any]],
    process: str,
    name_template: Optional[str] = None,
    used_names: Optional[Set[str]] = None,
    override_tag: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert a chain of outbound dicts to a proxy-like dict for proxies.json."""
    entry = chain[-1]  # entry point is last element
    mini_config = _build_chain_config(chain)
    tag = override_tag if override_tag is not None else entry.get("tag", "Chain")
    process_lower = str(process or "").lower()
    is_shielded_candidate = process_lower == "shielded" or any(
        bool(ob.get("_is_shielded")) for ob in chain if isinstance(ob, dict)
    )
    server = entry.get("server", "")
    try:
        port = int(entry.get("server_port", 0) or 0)
    except Exception:
        logging.getLogger(__name__).debug("Suppressed broad exception")
        port = 0
    tags = ["chain"]
    if any(ob.get("type") == "wireguard" for ob in chain):
        tags.append("warp")
    if is_shielded_candidate:
        tags.extend(["shielded", "candidate"])
    remarks = tag
    # Enrich from chain metadata (washer adds _origin_country_code, _origin_latency)
    origin_data: Dict[str, Any] = {}
    for ob in chain:
        if isinstance(ob, dict) and ob.get("_origin_country_code") is not None:
            origin_data["country_code"] = ob.get("_origin_country_code") or ""
            if ob.get("_origin_latency") is not None:
                origin_data["latency"] = ob["_origin_latency"]
            break
    details: Dict[str, Any] = {"is_chain": True}
    if origin_data:
        details["origin_proxy"] = origin_data
    if name_template:
        try:
            chain_proxy = Proxy(
                config=mini_config,
                protocol=entry.get("type", "chain"),
                address=str(server or ""),
                port=port,
                remarks=tag,
                is_working=not is_shielded_candidate,
                process=process,
                tags=tags.copy(),
                details=details,
            )
            remarks = format_proxy_name(name_template, chain_proxy)
        except Exception:
            logging.getLogger(__name__).debug("Suppressed broad exception")
            remarks = tag
    if used_names is not None:
        base_name = remarks or tag
        final_name = base_name
        suffix = (tag or "chain")[:16]
        idx = 1
        while final_name in used_names:
            idx += 1
            final_name = f"{base_name}-{suffix}-{idx}"
        used_names.add(final_name)
        remarks = final_name
    return {
        "id": tag,
        "protocol": "chain",
        "address": str(server or ""),
        "port": port,
        "uuid": "",
        "country": "",
        "country_code": "",
        "city": "",
        "asn": "",
        "org": "",
        "latency": None,
        "is_working": not is_shielded_candidate,
        "tags": tags,
        "last_checked": "",
        "source": None,
        "security": {},
        "details": {
            **details,
            "chain_process": process,
            "chain_depth": len(chain),
            "shielded_candidate": is_shielded_candidate,
            "shielded_verified": False,
        },
        "config": mini_config,
        "remarks": remarks,
        "process": process,
    }


def _chain_obs_to_entries(
    washed_outbounds: Optional[List[Dict[str, Any]]],
    smart_chains: Optional[Dict[str, List[List[Dict[str, Any]]]]],
    name_template: Optional[str] = None,
    used_names: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Convert washed outbounds and smart chains into proxy-like dicts
    so they appear in proxies.json for the frontend.
    """
    entries: List[Dict[str, Any]] = []
    seen_tags: set[str] = set()

    def _uniquify_entry_tag(tag: str) -> str:
        """Ensure each chain entry has a unique tag for proxies.json."""
        if not tag or tag not in seen_tags:
            return tag
        suffix = 0
        while f"{tag}-{suffix}" in seen_tags:
            suffix += 1
        return f"{tag}-{suffix}"

    def _is_proxy_like_entry(ob: Dict[str, Any]) -> bool:
        server = ob.get("server")
        if not isinstance(server, str) or not server.strip():
            return False
        try:
            port = int(ob.get("server_port", 0) or 0)
        except Exception:
            logging.getLogger(__name__).debug("Suppressed broad exception")
            return False
        return 1 <= port <= 65535

    # Washed outbounds (flat list → group into chains)
    if washed_outbounds:
        for chain in _group_chain_obs(washed_outbounds):
            if not chain:
                continue
            if not _is_proxy_like_entry(chain[-1]):
                continue
            entry_tag = chain[-1].get("tag", "")
            entry_tag = _uniquify_entry_tag(entry_tag)
            seen_tags.add(entry_tag)
            # Classify process type
            process = "washed"
            if any(
                "GOLD" in (ob.get("tag") or "") or "SHIELD" in (ob.get("tag") or "")
                for ob in chain
            ):
                process = "shielded"
            entries.append(
                _chain_to_proxy_entry(
                    chain,
                    process,
                    name_template=name_template,
                    used_names=used_names,
                    override_tag=entry_tag,
                )
            )

    # Smart chains (already grouped by category)
    if smart_chains:
        for _group, chain_list in smart_chains.items():
            for chain in chain_list:
                if not isinstance(chain, list) or not chain:
                    continue
                if not isinstance(chain[-1], dict) or not _is_proxy_like_entry(
                    chain[-1]
                ):
                    continue
                entry_tag = chain[-1].get("tag", "")
                entry_tag = _uniquify_entry_tag(entry_tag)
                seen_tags.add(entry_tag)
                entries.append(
                    _chain_to_proxy_entry(
                        chain,
                        "chain",
                        name_template=name_template,
                        used_names=used_names,
                        override_tag=entry_tag,
                    )
                )

    return entries


def _mark_shielded_lifecycle(proxy: Proxy, *, verified: bool) -> Proxy:
    """Normalize the public lifecycle contract for a shielded chain."""
    proxy.process = "shielded"
    proxy.is_working = verified
    details = dict(proxy.details or {})
    # ProxyWasher historically stores raw outbound dictionaries under
    # ``chain``.  The tester/serializer contract reads ``chain_outbounds``;
    # preserve the original key for compatibility while publishing the
    # canonical key used by downstream consumers.
    chain = details.get("chain")
    if isinstance(chain, list) and chain and "chain_outbounds" not in details:
        details["chain_outbounds"] = chain
    details.update(
        {
            "chain_process": "shielded",
            "shielded_candidate": True,
            "shielded_verified": verified,
        }
    )
    proxy.details = details
    proxy.tags = list(dict.fromkeys([*proxy.tags, "shielded", "candidate"]))
    return proxy


async def _verify_shielded_candidates(
    candidates: List[Proxy],
    tester: Optional["SingBoxTester"],
    stats: PipelineStats,
) -> List[Proxy]:
    """Verify candidates without dropping failed or missing result rows."""
    if tester is None:
        logger.debug(
            "No tester supplied; shielded candidates kept with is_working=False "
            "for user-side testing."
        )
        return candidates
    logger.info("🧪  Verifying %d shielded candidates...", len(candidates))
    try:
        results_by_object = {
            id(result): result for result in await tester.test_batch(candidates)
        }
        public_candidates = [
            _mark_shielded_lifecycle(
                results_by_object.get(id(candidate), candidate),
                verified=bool(
                    results_by_object.get(id(candidate), candidate).is_working
                ),
            )
            for candidate in candidates
        ]
    except Exception as verify_exc:
        logger.warning(
            "Shielded chain verification failed: %s",
            SecurityValidator.sanitize_log_message(str(verify_exc)),
        )
        return candidates
    stats.shielded_verified_count = sum(p.is_working for p in public_candidates)
    logger.info(
        "✅  Shielded Verification: %d/%d chains verified working.",
        stats.shielded_verified_count,
        len(candidates),
    )
    return public_candidates


def _save_proxies_with_chains(
    proxies: List[Proxy],
    path: Path,
    washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    smart_chains: Optional[Dict[str, List[List[Dict[str, Any]]]]] = None,
    name_template: Optional[str] = None,
) -> Dict[str, int]:
    """
    Save proxies.json with native proxies PLUS chain entries
    so the frontend shows all output types.
    """
    history = ProxyHistoryTracker()
    try:
        data = [serialize_proxy(p, history.get_history(p.id)) for p in proxies]
    finally:
        history.close()

    used_names: Set[str] = {
        str(item.get("remarks"))
        for item in data
        if isinstance(item, dict) and item.get("remarks")
    }
    chain_entries = _chain_obs_to_entries(
        washed_outbounds,
        smart_chains,
        name_template=name_template,
        used_names=used_names,
    )
    # Shielded chains are materialized as Proxy records before this function is
    # called so that verification state survives serialization.  Do not also
    # emit the raw outbound representation: it is always marked unverified and
    # would create a contradictory duplicate for a successfully tested chain.
    materialized_shielded_tags: Set[str] = set()
    for proxy in proxies:
        if proxy.process != "shielded":
            continue
        chain = chain_obs_from_details(proxy.details or {})
        if chain and isinstance(chain[-1], dict) and chain[-1].get("tag"):
            materialized_shielded_tags.add(str(chain[-1]["tag"]))
    if materialized_shielded_tags:
        chain_entries = [
            entry
            for entry in chain_entries
            if not (
                entry.get("process") == "shielded"
                and str(entry.get("id", "")) in materialized_shielded_tags
            )
        ]
    if chain_entries:
        data.extend(chain_entries)

    # CRITICAL: proxies.json must be JSON array (list of proxies), never single object
    if not isinstance(data, list):
        data = [data] if data is not None else []
    json_content = json.dumps(data, indent=2, ensure_ascii=False)
    AtomicFileWriter.write_text(path, json_content)
    return {
        "public_record_count": len(data),
        "public_working_count": sum(
            1
            for item in data
            if isinstance(item, dict) and bool(item.get("is_working"))
        ),
    }


async def _populate_resolved_ips(proxies: List[Proxy], settings: AppSettings) -> None:
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

    resolver = BatchDNSResolver(
        timeout=float(getattr(settings, "DNS_SAFE_RESOLVE_TIMEOUT", 4.0))
    )
    if resolver.resolver is None:
        logger.debug(
            "DNS-safe outputs: batch resolver unavailable; skipping DNS resolution."
        )
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
    tester: Optional["SingBoxTester"] = None,
):
    """
    Orchestrates the generation of all pipeline outputs.
    Integrates Tagging, Washing, Smart Chaining, and File Generation.

    Parameters
    ----------
    optimized_proxies:
        Deduplicated, sorted proxy list from the pipeline.
    output_path:
        Root directory for all generated output files.
    stats:
        Mutable stats object; updated in-place with washing/shielding metrics.
    history:
        Proxy history tracker used for sparklines and trend data.
    washer:
        Optional pre-initialised ProxyWasher.  A new instance is created when
        ``None`` is passed.
    tester:
        Optional SingBoxTester used to actively verify shielded chain
        candidates (P1-E).  When provided, shielded proxies that pass
        re-testing are appended to *optimized_proxies* and
        ``stats.shielded_verified_count`` is incremented accordingly.
        When ``None``, shielded candidates are still included in the output
        with ``is_working=False`` so end-users can try them on their own
        networks.
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

    # 0c. Log GeoIP enrichment statistics without loading the optional MMDB backend.
    _log_geoip_enrichment_stats(optimized_proxies)

    # 1. Initialize Washer & Scanner (The Intelligence Layer)
    # We load keys from Env. If empty, washer degrades gracefully to no-op.
    if washer is None:
        washer = ProxyWasher(settings.WARP_KEY_POOL)
        # Populate clean_ips in the washer (best-effort). This may involve network access
        # (scraper/scanner/static lists). Output generation must never fail if this step
        # is blocked by hostile network conditions.
        try:
            await washer.fetch_clean_ips()
        except Exception:
            logger.debug("Failed to fetch clean IPs (fail-open).", exc_info=True)

    # Export clean IPs for the frontend lab (best-effort, non-fatal).
    try:
        loop = asyncio.get_running_loop()
        clean_ips = washer.clean_ips
        if not clean_ips:
            # Provide a deterministic fallback for static hosting / merge-stage runs.
            from configstream.intelligence.washer.core import DEFAULT_CLEAN_IPS

            clean_ips = [(ip, 2408) for ip in DEFAULT_CLEAN_IPS]
        clean_ips_path = output_path / "data" / "clean_ips.json"
        await loop.run_in_executor(None, _save_clean_ips, clean_ips, clean_ips_path)
    except Exception:
        logger.debug("Failed to export clean_ips.json", exc_info=True)

    # Update stats with scanner results
    stats.scanner_ips_found = len(washer.clean_ips)

    # 2. Wash Batch (The "Blanket" Wash)
    # Generates standard WARP wraps for all working proxies
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
        logger.info(
            f"⚰️  Attempting to resurrect {len(failed_proxies)} dead proxies with Alchemy..."
        )
        try:
            shielded_outbounds, shielded_ids = washer.shield_batch(
                failed_proxies, stats=stats
            )
            if shielded_outbounds:
                logger.info(
                    f"✨  Alchemy Success! Resurrected {len(shielded_outbounds) // 2} candidates."
                )

                # P1-E: Truth in Metrics. Shielded chains are candidates until verified.
                # Create Proxy models for these candidates so they can be tested.
                shielded_proxies = []
                for i in range(0, len(shielded_outbounds), 2):
                    entry = shielded_outbounds[i]
                    exit_p = shielded_outbounds[i + 1]
                    # This helper builds a 'revived' proxy model from chain details
                    p = _mark_shielded_lifecycle(
                        washer.create_revived_proxy(entry, exit_p, "shielded"),
                        verified=False,
                    )
                    shielded_proxies.append(p)

                public_shielded_proxies = await _verify_shielded_candidates(
                    shielded_proxies, tester, stats
                )

                # Preserve every candidate as one public Proxy record.  Only
                # candidates with successful verification are working; failed,
                # missing, and exception-path results remain user-testable.
                optimized_proxies.extend(public_shielded_proxies)

                # Always track candidates and total created
                stats.shielded_count = len(shielded_ids)
                stats.shielded_candidate_count = len(shielded_ids)

                # Add ALL shielded outbounds for the output generation (preserved for user testing)
                washed_outbounds.extend(shielded_outbounds)
                washed_ids.update(shielded_ids)
            else:
                logger.info(
                    "No dead proxies could be resurrected (no WARP keys or clean IPs available)."
                )
        except Exception as e:
            logger.warning(
                "Shielding failed: %s", SecurityValidator.sanitize_log_message(str(e))
            )

    # Resolve and cache DNS variants after shielding has finalized the proxy pool.
    # Both modes need endpoint resolution; hardened-only deployments must not
    # depend on DNS_SAFE_OUTPUTS being enabled.
    if settings.DNS_SAFE_OUTPUTS or settings.DNS_HARDENED_OUTPUTS:
        await _populate_resolved_ips(optimized_proxies, settings)
    loop = asyncio.get_running_loop()
    _cached_dns_safe = await loop.run_in_executor(
        None, _build_dns_safe_proxies, optimized_proxies
    )
    _cached_dns_hardened = await loop.run_in_executor(
        None, _build_dns_hardened_proxies, optimized_proxies
    )
    stats.evasion_dns_safe_count = len(_cached_dns_safe[0])
    stats.evasion_dns_hardened_count = len(_cached_dns_hardened[0])

    # Track evasion metrics (count ALL TLS-capable proxies, not just working ones,
    # since evasion features are applied during output generation to all proxies)
    tls_proxies = [
        p
        for p in optimized_proxies
        if p.protocol in ["vmess", "vless", "trojan", "hysteria2", "tuic"]
    ]
    stats.evasion_utls_enabled = len(tls_proxies)
    stats.evasion_alpn_enabled = len(
        [p for p in tls_proxies if p.protocol in ["vmess", "vless", "trojan"]]
    )
    stats.evasion_fragmentation_enabled = 0  # sing-box removed tls_fragment
    stats.evasion_multiplexing_enabled = len(
        [
            p
            for p in tls_proxies
            if p.protocol in ["vmess", "vless", "trojan", "shadowsocks"]
        ]
    )

    # Explicit logging if no chains were created despite having working proxies
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

    await asyncio.to_thread(_rotate_proxy_snapshot, proxies_path, old_proxies_path)

    # Run blocking file I/O in executor
    loop = asyncio.get_running_loop()
    # Include washed outbounds + smart chains in proxies.json
    # so the frontend displays all output types (not just native proxies).
    public_counts = await loop.run_in_executor(
        None,
        _save_proxies_with_chains,
        optimized_proxies,
        proxies_path,
        washed_outbounds,
        smart_chains,
        tagger.template,
    )

    # DNS-safe dataset (IP-only) - reuse cached results from stats phase
    if _cached_dns_safe is not None:
        dns_safe_proxies, _ = _cached_dns_safe
    else:
        dns_safe_proxies, _ = _build_dns_safe_proxies(optimized_proxies)
    dns_safe_path: Path = output_path / "proxies-dns-safe.json"
    await loop.run_in_executor(None, save_json, dns_safe_proxies, dns_safe_path)

    # DNS-hardened dataset (prefer IP when available) - reuse cached results
    if _cached_dns_hardened is not None:
        dns_hardened_proxies, _ = _cached_dns_hardened
    else:
        dns_hardened_proxies, _ = _build_dns_hardened_proxies(optimized_proxies)
    dns_hardened_path: Path = output_path / "proxies-dns-hardened.json"
    await loop.run_in_executor(None, save_json, dns_hardened_proxies, dns_hardened_path)

    revived_proxies = [p for p in optimized_proxies if _is_revived(p)]
    # Always write revived datasets to avoid 404s and keep output contracts stable.
    revived_path: Path = output_path / "revived.json"
    await loop.run_in_executor(None, save_json, revived_proxies, revived_path)

    revived_dns_safe = [p for p in dns_safe_proxies if _is_revived(p)]
    revived_dns_path: Path = output_path / "revived-dns-safe.json"
    await loop.run_in_executor(None, save_json, revived_dns_safe, revived_dns_path)

    revived_dns_hardened = [p for p in dns_hardened_proxies if _is_revived(p)]
    revived_hardened_path: Path = output_path / "revived-dns-hardened.json"
    await loop.run_in_executor(
        None, save_json, revived_dns_hardened, revived_hardened_path
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
            dns_safe_cache=_cached_dns_safe,
            dns_hardened_cache=_cached_dns_hardened,
        ),
    )
    generated_files["revived"] = revived_path
    generated_files["proxies_dns_safe"] = dns_safe_path
    generated_files["proxies_dns_hardened"] = dns_hardened_path
    generated_files["revived_dns_safe"] = revived_dns_path
    generated_files["revived_dns_hardened"] = revived_hardened_path

    # 5. Metadata & Stats
    # Count unique chain outbound tags (revived + washed + smart chains)
    # Uses lightweight tag counting instead of duplicating the full
    # _append_chain collection logic from output_logic.py
    def _collect_tags(outbounds: list) -> set[str]:
        return {
            str(ob.get("tag"))
            for ob in outbounds
            if isinstance(ob, dict) and ob.get("tag")
        }

    _chain_tags: set[str] = set()
    for proxy in optimized_proxies:
        chain = chain_obs_from_details(proxy.details or {})
        if chain:
            _chain_tags |= _collect_tags(chain)
    if washed_outbounds:
        _chain_tags |= _collect_tags(washed_outbounds)
    if smart_chains:
        for chain_list in smart_chains.values():
            for chain in chain_list:
                if isinstance(chain, list):
                    _chain_tags |= _collect_tags(chain)
    stats.chain_obs_count = len(_chain_tags)

    stats_dict = stats.to_dict()
    if isinstance(public_counts, dict):
        stats_dict["public_record_count"] = int(
            public_counts.get("public_record_count", len(optimized_proxies))
        )
        stats_dict["public_working_count"] = int(
            public_counts.get("public_working_count", 0)
        )

    await loop.run_in_executor(
        None, save_metadata, stats_dict, optimized_proxies, output_path
    )

    # 5b. Vector map for frontend similarity search (with history for stability/reliability)
    await loop.run_in_executor(
        None,
        lambda: generate_vectors(optimized_proxies, output_path, history=history),
    )

    # 6. Stego Assets + Frontend Key Injection (optional)
    secret_key = settings.STEGO_KEY or settings.CONFIG_STREAM_KEY
    if isinstance(secret_key, str) and secret_key.strip() and len(secret_key) >= 20:
        frontend_root = (
            Path(settings.FRONTEND_DIR)
            if settings.FRONTEND_DIR
            else Path(__file__).resolve().parents[2] / "frontend"
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
    await loop.run_in_executor(
        None, history.export_evasion_trend, stats, evasion_trend_path
    )

    await loop.run_in_executor(None, write_public_artifact_contract, output_path)

    logger.info(f"Output generation complete. Files created in {output_path}")
    return generated_files
