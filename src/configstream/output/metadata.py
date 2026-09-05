# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import logging
import hashlib
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any
from importlib.metadata import version

from ..models import Proxy
from ..pipeline_stats import PipelineExecutionAudit
from ..converters.common import safe_int_conversion
from ..utils import AtomicFileWriter
from ..config import AppSettings
from ..serialize import serialize_proxy
from ..constants import (
    CHOSEN_TOTAL_TARGET,
    DropCategory,
    latency_bucket_for_ms,
)

logger = logging.getLogger(__name__)

PUBLIC_CONTRACT_SCHEMA_VERSION = "1.0"


def _json_snapshot_sha256(payload: Any) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_category(rel_path: str) -> str:
    if rel_path in {"metadata.json", "health.json", "artifact_manifest.json"}:
        return "control"
    if rel_path.startswith("api/"):
        return "api"
    if rel_path.startswith("assets/") or rel_path.endswith(".html"):
        return "frontend"
    if rel_path.startswith("docs/"):
        return "docs"
    if rel_path.startswith("data/"):
        return "analytics"
    if rel_path.endswith(".zip"):
        return "side-product"
    return "subscription"


def _read_json_object(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _artifact_timestamps(stats: Any) -> tuple[str, str, Any]:
    """Return generated_at, last_updated_utc, and start_time for metadata."""
    now_iso = datetime.now(timezone.utc).isoformat()
    generated_at_iso = now_iso
    start_time_iso = None
    if isinstance(stats, dict):
        start_time_iso = stats.get("start_time")
        if stats.get("end_time"):
            generated_at_iso = str(stats.get("end_time") or now_iso)
    elif getattr(stats, "end_time", None):
        generated_at_iso = stats.end_time.isoformat()
    return generated_at_iso, now_iso, start_time_iso


def _snapshot_hashes(proxies: List[Proxy], output_dir: Path) -> tuple[str, str | None]:
    proxies_snapshot_hash = _json_snapshot_sha256([serialize_proxy(p) for p in proxies])
    public_snapshot_path = output_dir / "proxies.json"
    if public_snapshot_path.is_file():
        public_snapshot = json.loads(public_snapshot_path.read_text(encoding="utf-8"))
        proxies_snapshot_hash = _json_snapshot_sha256(public_snapshot)
    old_snapshot_hash = None
    old_snapshot_path = output_dir / "proxies.old.json"
    if old_snapshot_path.is_file():
        try:
            old_payload = json.loads(old_snapshot_path.read_text(encoding="utf-8"))
            old_snapshot_hash = _json_snapshot_sha256(old_payload)
        except (OSError, json.JSONDecodeError):
            old_snapshot_hash = None

    return proxies_snapshot_hash, old_snapshot_hash


def _public_count(stats: Any, key: str, value: int, fallback: int) -> int:
    present = key in stats if isinstance(stats, dict) else hasattr(stats, key)
    return value if present else fallback


def _dict_value(
    stats: Dict[str, Any], key: str, alias: str = "", default: Any = 0
) -> Any:
    """Return an explicitly present value without treating zero as missing."""
    if key in stats:
        return stats[key]
    if alias and alias in stats:
        return stats[alias]
    return default


def _normalize_drop_reason(reason: str) -> str:
    key = (reason or "").strip().lower()
    if not key:
        return DropCategory.UNKNOWN.value
    if "duplicate" in key:
        return DropCategory.DUPLICATE.value
    if "invalid_protocol" in key:
        return DropCategory.INVALID_PROTOCOL.value
    if "invalid_port" in key:
        return DropCategory.INVALID_PORT.value
    if "missing_protocol_separator" in key:
        return DropCategory.MISSING_PROTOCOL_SEPARATOR.value
    if "implausible_format" in key:
        return DropCategory.IMPLAUSIBLE_FORMAT.value
    if "security" in key:
        return DropCategory.SECURITY_VALIDATION.value
    if "html" in key:
        return DropCategory.HTML_CONTENT.value
    if "hostile_payload" in key:
        return DropCategory.HOSTILE_PAYLOAD.value
    if "size_limit" in key:
        return DropCategory.SIZE_LIMIT_EXCEEDED.value
    if "backpressure" in key:
        return DropCategory.BACKPRESSURE_DROP.value
    if "tester_error" in key:
        return DropCategory.TESTER_ERROR.value
    if "fetch_error" in key:
        return DropCategory.FETCH_ERROR.value
    return key


def save_metadata(
    stats: Any,
    proxies: List[Proxy],
    output_dir: Path,
):
    """
    Saves metadata.json and other stats files.
    """
    meta_path = output_dir / "metadata.json"
    _meta_settings = AppSettings()

    # Single-pass loop to collect all stats at once
    total = len(proxies)
    working = 0
    lat_dist = {"fast": 0, "medium": 0, "slow": 0, "very_slow": 0}
    protocols: Dict[str, int] = {}
    countries: Dict[str, int] = {}
    asns: Dict[str, int] = {}
    latency_by_country_sum: Dict[str, float] = {}
    latency_by_country_count: Dict[str, int] = {}
    latency_by_protocol_sum: Dict[str, float] = {}
    latency_by_protocol_count: Dict[str, int] = {}

    for p in proxies:
        if not p.is_working:
            continue

        working += 1
        lat_dist[latency_bucket_for_ms(p.latency)] += 1
        protocols[p.protocol] = protocols.get(p.protocol, 0) + 1
        cc = p.country_code if p.country_code else "XX"
        countries[cc] = countries.get(cc, 0) + 1

        if p.latency is not None:
            latency_by_country_sum[cc] = latency_by_country_sum.get(cc, 0.0) + p.latency
            latency_by_country_count[cc] = latency_by_country_count.get(cc, 0) + 1
            proto_key = p.protocol or "unknown"
            latency_by_protocol_sum[proto_key] = (
                latency_by_protocol_sum.get(proto_key, 0.0) + p.latency
            )
            latency_by_protocol_count[proto_key] = (
                latency_by_protocol_count.get(proto_key, 0) + 1
            )

        if p.asn:
            asns[p.asn] = asns.get(p.asn, 0) + 1

    proxies_snapshot_hash, old_snapshot_hash = _snapshot_hashes(proxies, output_dir)

    # Extraction logic for stats
    total_sourced = total
    parsed_count = total
    tested_count = total
    reasons: Dict[str, int] = {}
    generated_at_iso, now_iso, start_time_iso = _artifact_timestamps(stats)
    end_time_iso = generated_at_iso
    washed_count = 0
    smart_chain_count = 0
    vwarp_win_rate = 0.0
    scanner_ips_found = 0
    fetched_sources = 0
    total_configured_sources = 0
    revived_warp = 0
    revived_vwarp = 0
    warp_attempts = 0
    vwarp_attempts = 0
    vwarp_success = 0
    duration_seconds = 0.0
    geo_resolved = 0
    cache_misses = 0
    final_count = 0
    chain_obs_count = 0
    time_limited = False
    time_limit_seconds = 0
    hard_timeout = False
    abandoned_queue_items = 0
    abandoned_queue_lines = 0
    shielded_count = 0
    shielded_candidate_count = 0
    shielded_verified_count = 0
    public_record_count = 0
    public_working_count = 0
    evasion_utls_enabled = 0
    evasion_alpn_enabled = 0
    evasion_fragmentation_enabled = 0
    evasion_multiplexing_enabled = 0
    evasion_dns_safe_count = 0
    evasion_dns_hardened_count = 0
    backpressure_drop = 0
    trace_id = "-"
    pipeline_execution_audit: Dict[str, Any] = {}

    if isinstance(stats, dict):
        total_sourced = safe_int_conversion(
            _dict_value(stats, "fetched_lines", "total_fetched", total)
        )
        parsed_count = stats.get("parsed", total)
        tested_count = stats.get("tested", total)
        raw_reasons = stats.get("rejection_reasons") or stats.get("drop_reasons") or {}
        if isinstance(raw_reasons, dict):
            reasons = {
                str(k): safe_int_conversion(v)
                for k, v in raw_reasons.items()
                if k is not None
            }
        washed_count = _dict_value(stats, "washed_chains", "washer_success_count")
        smart_chain_count = stats.get("smart_chain_count", 0)
        if not smart_chain_count and "smart_chains_breakdown" in stats:
            smart_chain_count = sum(stats["smart_chains_breakdown"].values())
        vwarp_win_rate = stats.get("vwarp_win_rate", 0.0)
        scanner_ips_found = stats.get("scanner_ips_found", 0)
        fetched_sources = stats.get("fetched_sources", 0)
        total_configured_sources = _dict_value(
            stats, "total_configured_sources", default=fetched_sources
        )
        revived_warp = stats.get("revived_warp", 0)
        revived_vwarp = stats.get("revived_vwarp", 0)
        warp_attempts = stats.get("warp_attempts", 0)
        vwarp_attempts = stats.get("vwarp_attempts", 0)
        vwarp_success = stats.get("vwarp_success", 0)
        duration_seconds = stats.get("duration", 0.0)
        geo_resolved = stats.get("geo_resolved", 0)
        cache_misses = stats.get("cache_misses", 0)
        final_count = stats.get("final_count", 0)
        chain_obs_count = stats.get("chain_obs_count", 0)
        time_limited = bool(stats.get("time_limited", False))
        time_limit_seconds = int(stats.get("time_limit_seconds", 0) or 0)
        hard_timeout = bool(stats.get("hard_timeout", False))
        abandoned_queue_items = int(stats.get("abandoned_queue_items", 0) or 0)
        abandoned_queue_lines = int(stats.get("abandoned_queue_lines", 0) or 0)
        shielded_count = stats.get("shielded_count", 0)
        shielded_candidate_count = int(
            _dict_value(stats, "shielded_candidate_count", default=shielded_count)
        )
        shielded_verified_count = stats.get("shielded_verified_count", 0)
        evasion_utls_enabled = stats.get("evasion_utls_enabled", 0)
        evasion_alpn_enabled = stats.get("evasion_alpn_enabled", 0)
        evasion_fragmentation_enabled = stats.get("evasion_fragmentation_enabled", 0)
        evasion_multiplexing_enabled = stats.get("evasion_multiplexing_enabled", 0)
        evasion_dns_safe_count = stats.get("evasion_dns_safe_count", 0)
        evasion_dns_hardened_count = stats.get("evasion_dns_hardened_count", 0)
        backpressure_drop = stats.get("backpressure_drop", 0)
        public_record_count = int(stats.get("public_record_count", 0) or 0)
        public_working_count = int(stats.get("public_working_count", 0) or 0)
        trace_id = str(stats.get("trace_id") or "-")
        audit_obj = stats.get("pipeline_execution_audit")
        if isinstance(audit_obj, dict):
            pipeline_execution_audit = dict(audit_obj)
        start_time_iso = stats.get("start_time")
        if stats.get("end_time"):
            generated_at_iso = str(stats.get("end_time") or now_iso)
            end_time_iso = generated_at_iso
    else:
        # PipelineStats object
        total_sourced = getattr(
            stats, "fetched_lines", getattr(stats, "total_sourced", total)
        )
        parsed_count = getattr(stats, "parsed", total)
        tested_count = getattr(stats, "tested", total)
        reasons = getattr(stats, "drop_reasons", {})
        washed_count = getattr(stats, "washer_success_count", 0)
        smart_chain_count = getattr(stats, "smart_chain_count", 0)
        vwarp_win_rate = getattr(stats, "vwarp_win_rate", 0.0)
        scanner_ips_found = getattr(stats, "scanner_ips_found", 0)
        fetched_sources = getattr(stats, "fetched_sources", 0)
        total_configured_sources = (
            getattr(stats, "total_configured_sources", 0) or fetched_sources
        )
        revived_warp = getattr(stats, "revived_warp", 0)
        revived_vwarp = getattr(stats, "revived_vwarp", 0)
        warp_attempts = getattr(stats, "warp_attempts", 0)
        vwarp_attempts = getattr(stats, "vwarp_attempts", 0)
        vwarp_success = getattr(stats, "vwarp_success", 0)
        duration_seconds = getattr(stats, "duration", 0.0)
        geo_resolved = getattr(stats, "geo_resolved", 0)
        cache_misses = getattr(stats, "cache_misses", 0)
        final_count = getattr(stats, "final_count", 0)
        chain_obs_count = getattr(stats, "chain_obs_count", 0)
        time_limited = bool(getattr(stats, "time_limited", False))
        time_limit_seconds = int(getattr(stats, "time_limit_seconds", 0) or 0)
        hard_timeout = bool(getattr(stats, "hard_timeout", False))
        abandoned_queue_items = int(getattr(stats, "abandoned_queue_items", 0) or 0)
        abandoned_queue_lines = int(getattr(stats, "abandoned_queue_lines", 0) or 0)
        shielded_count = getattr(stats, "shielded_count", 0)
        shielded_candidate_count = getattr(
            stats, "shielded_candidate_count", shielded_count
        )
        shielded_verified_count = getattr(stats, "shielded_verified_count", 0)
        evasion_utls_enabled = getattr(stats, "evasion_utls_enabled", 0)
        evasion_alpn_enabled = getattr(stats, "evasion_alpn_enabled", 0)
        evasion_fragmentation_enabled = getattr(
            stats, "evasion_fragmentation_enabled", 0
        )
        evasion_multiplexing_enabled = getattr(stats, "evasion_multiplexing_enabled", 0)
        evasion_dns_safe_count = getattr(stats, "evasion_dns_safe_count", 0)
        evasion_dns_hardened_count = getattr(stats, "evasion_dns_hardened_count", 0)
        backpressure_drop = getattr(stats, "backpressure_drop", 0)
        trace_id = str(getattr(stats, "trace_id", "-") or "-")
        public_record_count = int(getattr(stats, "public_record_count", 0) or 0)
        public_working_count = int(getattr(stats, "public_working_count", 0) or 0)
        audit_obj = getattr(stats, "pipeline_execution_audit", None)
        if isinstance(audit_obj, dict):
            pipeline_execution_audit = dict(audit_obj)
        if not pipeline_execution_audit:
            pipeline_execution_audit = PipelineExecutionAudit.from_stats(
                stats
            ).to_dict()
        if hasattr(stats, "working") and stats.working > 0:
            working = stats.working

    normalized_reasons: Dict[str, int] = {}
    for reason_key, reason_count in (reasons or {}).items():
        category = _normalize_drop_reason(str(reason_key))
        normalized_reasons[category] = normalized_reasons.get(category, 0) + int(
            reason_count or 0
        )
    reasons = normalized_reasons

    smart_chains_breakdown = {}
    if isinstance(stats, dict) and "smart_chains_breakdown" in stats:
        smart_chains_breakdown = stats["smart_chains_breakdown"]

    try:
        pkg_version = version("configstream")
    except Exception:
        logging.getLogger(__name__).debug("Suppressed broad exception")
        pkg_version = "unknown"

    update_interval_hours = _meta_settings.UPDATE_INTERVAL_HOURS

    latency_by_country = {
        cc: round(latency_by_country_sum[cc] / latency_by_country_count[cc])
        for cc in latency_by_country_sum
        if latency_by_country_count.get(cc)
    }
    latency_by_protocol = {
        proto: round(latency_by_protocol_sum[proto] / latency_by_protocol_count[proto])
        for proto in latency_by_protocol_sum
        if latency_by_protocol_count.get(proto)
    }

    total_revived_count = (
        stats.get("total_revived", revived_warp + revived_vwarp)
        if isinstance(stats, dict)
        else getattr(stats, "total_revived", revived_warp + revived_vwarp)
    )

    washing_enabled = False
    warp_pool_raw = _meta_settings.WARP_KEY_POOL
    if isinstance(warp_pool_raw, str) and warp_pool_raw.strip():
        try:
            warp_pool = json.loads(warp_pool_raw)
            washing_enabled = isinstance(warp_pool, list) and len(warp_pool) > 0
        except json.JSONDecodeError:
            washing_enabled = True
    washing_enabled = washing_enabled or vwarp_attempts > 0

    logical_total_proxies = total + smart_chain_count
    exported_total_proxies = _public_count(
        stats, "public_record_count", public_record_count, logical_total_proxies
    )
    exported_total_working = _public_count(
        stats, "public_working_count", public_working_count, working
    )

    meta = {
        "schema_version": "3.0.2",
        "version": pkg_version,
        "total_proxies": exported_total_proxies,
        "logical_total_proxies": logical_total_proxies,
        "total_tested": tested_count,
        "total_working": exported_total_working,
        "logical_total_working": working,
        "success_rate": (
            (exported_total_working / tested_count) if tested_count > 0 else 0
        ),
        "generated_at": generated_at_iso,
        "last_updated_utc": now_iso,
        "trace_id": trace_id,
        "proxies_snapshot_hash": proxies_snapshot_hash,
        "previous_proxies_snapshot_hash": old_snapshot_hash,
        "latency_distribution": lat_dist,
        "protocols": protocols,
        "country_stats": countries,
        "countries": countries,
        "rejection_reasons": reasons,
        "drop_reasons": reasons,
        "asns": asns,
        "isp_stats": asns,
        "total_revived": total_revived_count,
        "total_clean": max(0, working - total_revived_count),
        "total_smart_chains": smart_chain_count,
        "smart_chains_breakdown": smart_chains_breakdown,
        "total_dirty": sum(
            [
                int(reasons.get("dirty_ip", 0) or 0),
                int(reasons.get("DIRTY_IP", 0) or 0),
                int(reasons.get("honeypot", 0) or 0),
                int(reasons.get("HONEYPOT", 0) or 0),
            ]
        ),
        "vwarp_win_rate": vwarp_win_rate,
        "scanner_ips_found": scanner_ips_found,
        "washer_success_count": washed_count,
        "smart_chain_count": smart_chain_count,
        "chain_obs_count": chain_obs_count,
        "chain_outbounds_count": chain_obs_count,
        "public_record_count": exported_total_proxies,
        "public_working_count": exported_total_working,
        "backpressure_drop": backpressure_drop,
        "revived_warp": revived_warp,
        "revived_vwarp": revived_vwarp,
        "warp_attempts": warp_attempts,
        "vwarp_attempts": vwarp_attempts,
        "vwarp_success": vwarp_success,
        "washing_enabled": washing_enabled,
        "shielded_count": getattr(stats, "shielded_count", shielded_count),
        "shielded_candidate_count": shielded_candidate_count,
        "shielded_verified_count": shielded_verified_count,
        "evasion_utls_enabled": evasion_utls_enabled,
        "evasion_alpn_enabled": evasion_alpn_enabled,
        "evasion_fragmentation_enabled": evasion_fragmentation_enabled,
        "evasion_multiplexing_enabled": evasion_multiplexing_enabled,
        "evasion_dns_safe_count": evasion_dns_safe_count,
        "evasion_dns_hardened_count": evasion_dns_hardened_count,
        "start_time": start_time_iso,
        "end_time": end_time_iso,
        "duration": duration_seconds,
        "duration_seconds": duration_seconds,
        "geo_resolved": geo_resolved,
        "cache_misses": cache_misses,
        "final_count": final_count or working,
        "time_limited": time_limited,
        "time_limit_seconds": time_limit_seconds,
        "hard_timeout": hard_timeout,
        "abandoned_queue_items": abandoned_queue_items,
        "abandoned_queue_lines": abandoned_queue_lines,
        "total_lines_sourced": total_sourced,
        "total_unique_candidates": parsed_count,
        "total_valid_proxies": working,
        "total_configured_sources": total_configured_sources,
        "fetched_sources": fetched_sources,
        "sources_count": total_configured_sources,
        "total_sources": total_configured_sources,
        "update_interval_hours": update_interval_hours,
        "latency_by_country": latency_by_country,
        "latency_by_protocol": latency_by_protocol,
        "fetched_lines": total_sourced,
        "parsed": parsed_count,
        "tested": tested_count,
        "working": working,
        "chosen_subset_size": min(
            working if working > 0 else len(proxies),
            (
                CHOSEN_TOTAL_TARGET
                if CHOSEN_TOTAL_TARGET > 0
                else (working if working > 0 else len(proxies))
            ),
        ),
        "pipeline_execution_audit": pipeline_execution_audit,
    }

    AtomicFileWriter.write_text(
        meta_path, json.dumps(meta, indent=2, ensure_ascii=False)
    )


def _attach_manifest_signature(manifest: Dict[str, Any]) -> None:
    private_key_hex = os.environ.get("CS_SIGNING_PRIVATE_KEY_HEX")
    if not private_key_hex:
        return

    from ..signer import Signer
    from ..security_validator import SecurityValidator

    try:
        signer = Signer(private_key_hex)
        manifest["manifest_signature"] = signer.sign_manifest(manifest)
    except Exception as exc:
        safe_msg = SecurityValidator.sanitize_log_message(str(exc))
        logger.error(
            "Failed to sign manifest [%s]: %s",
            type(exc).__name__,
            safe_msg,
        )
        raise RuntimeError(f"Configured manifest signing failed: {safe_msg}") from exc


def write_public_artifact_contract(output_dir: Path) -> Dict[str, Any]:
    """
    Write health.json and artifact_manifest.json for the public output directory.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = _read_json_object(output_dir / "metadata.json")
    now_iso = datetime.now(timezone.utc).isoformat()
    generated_at = str(
        metadata.get("last_updated_utc") or metadata.get("generated_at") or now_iso
    )
    trace_id = str(metadata.get("trace_id") or "-")

    health: Dict[str, Any] = {
        "schema_version": PUBLIC_CONTRACT_SCHEMA_VERSION,
        "status": (
            "degraded" if int(metadata.get("total_working", 0) or 0) == 0 else "ok"
        ),
        "generated_at": generated_at,
        "trace_id": trace_id,
        "source_commit": os.environ.get("GITHUB_SHA", ""),
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        "total_working": int(metadata.get("total_working", 0) or 0),
        "total_tested": int(metadata.get("total_tested", 0) or 0),
        "schema_validated": False,
        "notes": [],
    }
    AtomicFileWriter.write_text(
        output_dir / "health.json", json.dumps(health, indent=2, ensure_ascii=False)
    )

    files: List[Dict[str, Any]] = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(output_dir).as_posix()
        if rel_path == "artifact_manifest.json" or rel_path.endswith(".tmp"):
            continue
        files.append(
            {
                "path": rel_path,
                "size_bytes": path.stat().st_size,
                "sha256": _file_sha256(path),
                "category": _artifact_category(rel_path),
            }
        )

    manifest = {
        "schema_version": PUBLIC_CONTRACT_SCHEMA_VERSION,
        "generated_at": generated_at,
        "artifact_generated_at": generated_at,
        "trace_id": trace_id,
        "source_commit": os.environ.get("GITHUB_SHA", ""),
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        "file_count": len(files),
        "total_size_bytes": sum(item["size_bytes"] for item in files),
        "files": files,
    }
    _attach_manifest_signature(manifest)
    AtomicFileWriter.write_text(
        output_dir / "artifact_manifest.json",
        json.dumps(manifest, indent=2, ensure_ascii=False),
    )
    return manifest


def generate_metadata_json(stats: Any, proxies: List[Proxy], output_dir: Path):
    save_metadata(stats, proxies, output_dir)


def generate_health_json(output_dir: Path):
    write_public_artifact_contract(output_dir)
