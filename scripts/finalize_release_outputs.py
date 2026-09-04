# SPDX-License-Identifier: AGPL-3.0-or-later
"""Normalize, sanitize, and contract-check public release outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from configstream.constants import is_tester_infrastructure_drop_reason
from configstream.output.client_formats import generate_xray_config

try:
    from scripts.public_client_configs import (
        discover_mihomo_configs,
        discover_singbox_configs,
        resolve_public_config,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from public_client_configs import (  # type: ignore[no-redef]
        discover_mihomo_configs,
        discover_singbox_configs,
        resolve_public_config,
    )

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
TRANSIENT_SUFFIXES = (".lock", ".tmp", ".log", ".pyc", ".pyo", ".swp")
INTERNAL_KEYS = {
    "_source",
    "source_url",
    "subscription_url",
    "origin_url",
    "fetch_url",
    "raw_source",
    "tester_error_category",
    "infra_failure",
    "failure_category",
}
MAX_SELECTOR_MEMBERS = int(os.environ.get("MAX_SELECTOR_MEMBERS", "96"))


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _clean_text(value: str) -> str:
    return CONTROL_RE.sub("", unicodedata.normalize("NFC", value))


def _source_host(value: Any) -> Any:
    if not isinstance(value, str) or not value:
        return None
    parsed = urlparse(value)
    if parsed.hostname:
        return parsed.hostname.lower()
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:12]


def _sanitize(value: Any, *, key: str | None = None) -> Any:
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for raw_key, item in value.items():
            item_key = str(raw_key)
            if item_key.startswith("_") or item_key.lower() in INTERNAL_KEYS:
                continue
            output[item_key] = _sanitize(item, key=item_key)
        return output
    if isinstance(value, list):
        return [_sanitize(item, key=key) for item in value]
    if isinstance(value, str):
        value = _clean_text(value)
        if key == "source" or (key and "source" in key.lower()):
            return _source_host(value)
        return value
    return value


def _string_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)]


def _wireguard_endpoint(outbound: dict[str, Any]) -> dict[str, Any]:
    local = _string_list(outbound.get("address") or outbound.get("local_address"))
    allowed = _string_list(outbound.get("allowed_ips")) or ["0.0.0.0/0"]
    if any(":" in item for item in local) and "::/0" not in allowed:
        allowed.append("::/0")
    peer: dict[str, Any] = {
        "address": outbound.get("server"),
        "port": int(outbound.get("server_port") or 0),
        "public_key": outbound.get("peer_public_key") or outbound.get("public_key"),
        "allowed_ips": allowed,
    }
    for field in ("pre_shared_key", "reserved", "persistent_keepalive_interval"):
        if outbound.get(field) not in (None, "", []):
            peer[field] = outbound[field]
    endpoint: dict[str, Any] = {
        "type": "wireguard",
        "tag": outbound.get("tag"),
        "address": local,
        "private_key": outbound.get("private_key"),
        "mtu": int(outbound.get("mtu") or 1408),
        "peers": [peer],
    }
    for field in (
        "detour",
        "bind_interface",
        "routing_mark",
        "connect_timeout",
        "tcp_fast_open",
        "tcp_multi_path",
        "udp_fragment",
        "domain_resolver",
    ):
        if field in outbound:
            endpoint[field] = outbound[field]
    sanitized = _sanitize(endpoint)
    return sanitized if isinstance(sanitized, dict) else {}


def _dns_server(server: dict[str, Any]) -> dict[str, Any]:
    if server.get("type") and "address" not in server:
        sanitized = _sanitize(server)
        return sanitized if isinstance(sanitized, dict) else {}
    address = str(server.get("address") or server.get("server") or "local")
    parsed = urlparse(address)
    if address == "local":
        result: dict[str, Any] = {"type": "local"}
    elif address.startswith("rcode://"):
        result = {"type": "rcode", "rcode": address.split("://", 1)[1]}
    elif parsed.scheme in {"https", "tls", "quic", "h3", "tcp", "udp"}:
        result = {
            "type": parsed.scheme,
            "server": parsed.hostname or parsed.path,
        }
        if parsed.port:
            result["server_port"] = parsed.port
        if parsed.scheme == "https" and parsed.path and parsed.path != "/":
            result["path"] = parsed.path
    else:
        result = {"type": "udp", "server": address}
    for field in ("tag", "detour", "client_subnet"):
        if server.get(field) not in (None, ""):
            result[field] = server[field]
    sanitized = _sanitize(result)
    return sanitized if isinstance(sanitized, dict) else {}


def modernize_singbox(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    sanitized = _sanitize(payload)
    config: dict[str, Any] = sanitized if isinstance(sanitized, dict) else {}
    endpoints = [item for item in config.get("endpoints", []) if isinstance(item, dict)]
    outbounds: list[dict[str, Any]] = []
    for outbound in config.get("outbounds", []):
        if not isinstance(outbound, dict):
            continue
        kind = outbound.get("type")
        if kind == "wireguard":
            endpoints.append(_wireguard_endpoint(outbound))
        elif kind not in {"block", "dns"}:
            outbounds.append(outbound)
    config["outbounds"] = outbounds
    if endpoints:
        config["endpoints"] = endpoints
    else:
        config.pop("endpoints", None)

    for inbound in config.get("inbounds", []):
        if not isinstance(inbound, dict) or inbound.get("type") != "tun":
            continue
        addresses = _string_list(inbound.pop("inet4_address", None))
        addresses.extend(_string_list(inbound.pop("inet6_address", None)))
        if addresses:
            inbound["address"] = addresses
        routes = _string_list(inbound.pop("inet4_route_address", None))
        routes.extend(_string_list(inbound.pop("inet6_route_address", None)))
        if routes:
            inbound["route_address"] = routes

    dns = config.get("dns")
    if isinstance(dns, dict):
        dns.pop("independent_cache", None)
        dns["servers"] = [
            _dns_server(item)
            for item in dns.get("servers", [])
            if isinstance(item, dict)
        ]
        dns_rules: list[dict[str, Any]] = []
        for item in dns.get("rules", []):
            if not isinstance(item, dict):
                continue
            sanitized_rule = _sanitize(item)
            rule: dict[str, Any] = (
                sanitized_rule if isinstance(sanitized_rule, dict) else {}
            )
            if rule.get("server") == "block_dns":
                rule.pop("server", None)
                rule["action"] = "reject"
            elif "server" in rule and "action" not in rule:
                rule["action"] = "route"
            dns_rules.append(rule)
        dns["rules"] = dns_rules

    route_value = config.get("route")
    route: dict[str, Any] = route_value if isinstance(route_value, dict) else {}
    rules: list[dict[str, Any]] = []
    for item in route.get("rules", []):
        if not isinstance(item, dict):
            continue
        sanitized_rule = _sanitize(item)
        rule = sanitized_rule if isinstance(sanitized_rule, dict) else {}
        protocols = _string_list(rule.get("protocol"))
        if rule.get("outbound") == "block":
            rule.pop("outbound", None)
            rule["action"] = "reject"
        elif rule.get("outbound") == "dns-out" and "dns" in protocols:
            rule.pop("outbound", None)
            rule["action"] = "hijack-dns"
        elif "outbound" in rule and "action" not in rule:
            rule["action"] = "route"
        rules.append(rule)
    if config.get("inbounds") and not any(
        item.get("action") == "sniff" for item in rules
    ):
        rules.insert(0, {"action": "sniff"})
    if config.get("inbounds") and not any(
        item.get("action") == "hijack-dns" for item in rules
    ):
        rules.insert(1, {"protocol": "dns", "action": "hijack-dns"})
    route["rules"] = rules
    tags = [
        str(item.get("tag")) for item in [*outbounds, *endpoints] if item.get("tag")
    ]
    preferred = next(
        (
            tag
            for tag in ("🌍 Proxy Select", "🚀 Mode Selector", "🚀 Auto")
            if tag in tags
        ),
        None,
    )
    route["final"] = (
        route.get("final")
        or preferred
        or next((tag for tag in tags if tag != "direct"), "direct")
    )
    config["route"] = route

    known = set(tags)
    retained_outbounds: list[dict[str, Any]] = []
    for outbound in outbounds:
        if outbound.get("type") not in {"selector", "urltest"}:
            retained_outbounds.append(outbound)
            continue
        members = outbound.get("outbounds")
        if not isinstance(members, list):
            continue
        unique: list[str] = []
        for member in members:
            tag = str(member)
            if tag in known and tag not in unique:
                unique.append(tag)
            if len(unique) >= MAX_SELECTOR_MEMBERS:
                break
        if not unique and "direct" in known:
            unique = ["direct"]
        if not unique:
            continue
        outbound["outbounds"] = unique
        if outbound.get("default") not in unique:
            outbound.pop("default", None)
        retained_outbounds.append(outbound)
    config["outbounds"] = retained_outbounds
    return config


def _repair_clash(root: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    if yaml is None:
        return {"status": "skipped", "reason": "PyYAML unavailable"}
    added = 0
    repaired_files: list[str] = []
    for path in discover_mihomo_configs(root):
        resolved, path_error = resolve_public_config(root, path)
        if resolved is None:
            raise ValueError(
                f"refusing to rewrite unsafe client config "
                f"{path.relative_to(root)}: {path_error}"
            )
        loaded = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
        payload: dict[str, Any] = loaded if isinstance(loaded, dict) else {}
        raw_proxies = payload.get("proxies")
        proxies: list[Any] = raw_proxies if isinstance(raw_proxies, list) else []
        names = {str(item.get("name")) for item in proxies if isinstance(item, dict)}
        new_names: list[str] = []
        for record in records:
            protocol = str(record.get("protocol") or "").lower()
            if not record.get("is_working") or protocol not in {
                "http",
                "socks",
                "socks5",
            }:
                continue
            name = _clean_text(
                str(record.get("remarks") or record.get("id") or "Proxy")
            )
            if name in names:
                continue
            raw_details = record.get("details")
            details: dict[str, Any] = (
                raw_details if isinstance(raw_details, dict) else {}
            )
            item: dict[str, Any] = {
                "name": name,
                "type": "socks5" if protocol.startswith("socks") else "http",
                "server": record.get("address"),
                "port": int(record.get("port") or 0),
            }
            user = record.get("uuid") or details.get("username") or details.get("user")
            if user:
                item.update(
                    {"username": user, "password": details.get("password") or ""}
                )
            proxies.append(item)
            names.add(name)
            new_names.append(name)
            added += 1
        payload["proxies"] = proxies
        raw_groups = payload.get("proxy-groups")
        groups = raw_groups if isinstance(raw_groups, list) else []
        for group in groups:
            if not isinstance(group, dict):
                continue
            raw_group_proxies = group.get("proxies")
            if not isinstance(raw_group_proxies, list):
                continue
            raw_group_proxies.extend(
                name for name in new_names if name not in raw_group_proxies
            )
        resolved.write_text(
            yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        repaired_files.append(path.relative_to(root).as_posix())
    return {
        "status": "generated",
        "added_http_socks": added,
        "repaired_files": repaired_files,
    }


def _cleanup(root: Path) -> list[str]:
    removed: list[str] = []
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_file() and path.name.endswith(TRANSIENT_SUFFIXES):
            removed.append(path.relative_to(root).as_posix())
            path.unlink(missing_ok=True)
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {
            ".json",
            ".jsonl",
            ".yaml",
            ".yml",
            ".conf",
            ".txt",
            ".md",
            ".html",
        }:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        clean = CONTROL_RE.sub("", text)
        if clean != text:
            path.write_text(clean, encoding="utf-8")
    return removed


def _blockers(metadata: dict[str, Any], threshold: float) -> list[str]:
    reasons: list[str] = []
    configured = int(
        metadata.get("total_configured_sources") or metadata.get("total_sources") or 0
    )
    fetched = int(metadata.get("fetched_sources") or 0)
    coverage = fetched / configured if configured else 0.0
    if configured and coverage < threshold:
        reasons.append(
            f"source_coverage_below_threshold:{coverage:.4f}<{threshold:.4f}"
        )
    # metadata.time_limited is deliberately NOT a blocker: it means source
    # intake stopped at the batch window, not that published proxies are bad.
    # Every emitted proxy still passed testing, native-client validation, and
    # the coverage gate below. The gate classifies the residual
    # "pipeline_time_limited" note as non-blocking (see release_gate).
    tester_errors = 0
    drop_reasons = metadata.get("drop_reasons")
    if isinstance(drop_reasons, dict):
        for key, value in drop_reasons.items():
            if is_tester_infrastructure_drop_reason(key):
                tester_errors += int(value or 0)
    if tester_errors:
        reasons.append(f"tester_errors:{tester_errors}")
    candidates = int(
        metadata.get("shielded_candidate_count") or metadata.get("shielded_count") or 0
    )
    verified = int(metadata.get("shielded_verified_count") or 0)
    if candidates > verified:
        reasons.append(f"unverified_shielded_candidates:{candidates - verified}")
    return reasons


def finalize(root: Path, repo_root: Path, threshold: float) -> None:
    raw = _load(root / "proxies.json", [])
    records: list[dict[str, Any]] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            sanitized = _sanitize(item)
            if isinstance(sanitized, dict):
                records.append(sanitized)
    for record in records:
        config = record.get("config")
        if isinstance(config, str) and config.lstrip().startswith("{"):
            try:
                record["config"] = json.dumps(
                    modernize_singbox(json.loads(config)),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            except json.JSONDecodeError:
                pass
    _write(root / "proxies.json", records)

    modernized: list[str] = []
    for path in discover_singbox_configs(root):
        resolved, path_error = resolve_public_config(root, path)
        if resolved is None:
            raise ValueError(
                f"refusing to rewrite unsafe client config "
                f"{path.relative_to(root)}: {path_error}"
            )
        payload = _load(resolved)
        if isinstance(payload, dict):
            _write(resolved, modernize_singbox(payload))
            modernized.append(path.relative_to(root).as_posix())

    xray, xray_report = generate_xray_config(records)
    _write(root / "xray.json", xray)
    clash_report = _repair_clash(root, records)
    copied_wasm: list[str] = []
    wasm_candidates: list[tuple[Path, Path]] = [
        (
            repo_root / "frontend/assets/wasm/tester.wasm",
            root / "assets/wasm/tester.wasm",
        ),
        (
            repo_root / "frontend/assets/js/wasm_exec.js",
            root / "assets/js/wasm_exec.js",
        ),
        # Legacy fallback locations retained for local runs
        (repo_root / "wasm/tester.wasm", root / "assets/wasm/tester.wasm"),
        (repo_root / "js/wasm_exec.js", root / "assets/js/wasm_exec.js"),
    ]
    for source, destination in wasm_candidates:
        if source.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            # Atomic copy to avoid half-written wasm on sudden termination
            tmp = destination.with_suffix(destination.suffix + ".tmp")
            shutil.copy2(source, tmp)
            tmp.replace(destination)
            rel = destination.relative_to(root).as_posix()
            if rel not in copied_wasm:
                copied_wasm.append(rel)
    removed = _cleanup(root)

    logical = [item for item in records if item.get("protocol") != "chain"]
    logical_working = sum(bool(item.get("is_working")) for item in logical)
    exported_working = sum(bool(item.get("is_working")) for item in records)
    loaded_metadata = _load(root / "metadata.json", {})
    metadata: dict[str, Any] = (
        loaded_metadata if isinstance(loaded_metadata, dict) else {}
    )
    tested = int(metadata.get("total_tested") or metadata.get("tested") or 0)
    configured = int(
        metadata.get("total_configured_sources") or metadata.get("total_sources") or 0
    )
    fetched = int(metadata.get("fetched_sources") or 0)
    now_iso = datetime.now(timezone.utc).isoformat()
    if not str(metadata.get("generated_at") or "").strip():
        metadata["generated_at"] = now_iso
    metadata["last_updated_utc"] = now_iso
    metadata.update(
        {
            "schema_version": "3.1.0",
            "total_proxies": len(logical),
            "logical_total_proxies": len(logical),
            "exported_record_count": len(records),
            "public_record_count": len(records),
            "total_working": logical_working,
            "logical_total_working": logical_working,
            "exported_working_record_count": exported_working,
            "public_working_count": exported_working,
            "success_rate": logical_working / tested if tested else 0.0,
            "source_coverage": fetched / configured if configured else 0.0,
            "record_semantics": {
                "total_proxies": "logical non-chain records",
                "total_working": "logical working non-chain records",
                "exported_record_count": "all public records including generated chain rows",
            },
        }
    )
    _write(root / "metadata.json", metadata)

    compatibility: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "targets": {
            "sing-box": {
                "status": "generated",
                "target": "1.13.14",
                "wireguard_model": "top-level endpoints",
                "modernized_files": modernized,
            },
            "xray": xray_report,
            "mihomo": clash_report,
            "surge": {"status": "generated"},
            "loon": {"status": "generated"},
            "quantumult-x": {"status": "generated"},
            "sip008": {
                "status": "protocol-limited",
                "scope": "Shadowsocks only by SIP008 design",
            },
        },
        "wasm": {"copied": copied_wasm},
        "artifact_hygiene": {"removed": removed},
    }
    _write(root / "format_compatibility.json", compatibility)

    reasons = _blockers(metadata, threshold)
    generated_at = str(
        metadata.get("last_updated_utc")
        or metadata.get("generated_at")
        or datetime.now(timezone.utc).isoformat()
    )
    health: dict[str, Any] = {
        "schema_version": "2.0",
        "status": "degraded",
        "generated_at": generated_at,
        "trace_id": str(metadata.get("trace_id") or "-"),
        "source_commit": os.environ.get("GITHUB_SHA", ""),
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        "total_working": logical_working,
        "total_tested": tested,
        "source_coverage": metadata.get("source_coverage"),
        "schema_validated": False,
        "native_clients_validated": False,
        "release_blockers": reasons,
        "notes": ["Promoted to ok only by scripts/release_gate.py"],
    }
    _write(root / "health.json", health)
    (root / "api").mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / "proxies.json", root / "api/proxies")
    shutil.copy2(root / "metadata.json", root / "api/stats")

    files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if (
            not path.is_file()
            or path.name == "artifact_manifest.json"
            or path.name.endswith(TRANSIENT_SUFFIXES)
        ):
            continue
        rel = path.relative_to(root).as_posix()
        files.append(
            {
                "path": rel,
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
                "category": (
                    "control"
                    if rel
                    in {"metadata.json", "health.json", "format_compatibility.json"}
                    else "artifact"
                ),
            }
        )
    _write(
        root / "artifact_manifest.json",
        {
            "schema_version": "2.0",
            "generated_at": generated_at,
            "source_commit": os.environ.get("GITHUB_SHA", ""),
            "run_id": os.environ.get("GITHUB_RUN_ID", ""),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
            "file_count": len(files),
            "total_size_bytes": sum(item["size_bytes"] for item in files),
            "files": files,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--min-source-coverage",
        type=float,
        default=float(os.environ.get("MIN_SOURCE_COVERAGE", "0.80")),
    )
    args = parser.parse_args()
    finalize(
        args.artifact_dir.resolve(),
        args.repo_root.resolve(),
        max(0.0, min(args.min_source_coverage, 1.0)),
    )
    print(f"Finalized release artifact at {args.artifact_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
