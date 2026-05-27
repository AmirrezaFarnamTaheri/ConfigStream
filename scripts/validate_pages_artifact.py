# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate the static GitHub Pages artifact before deployment."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import cast
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - PyYAML is a normal dependency.
    yaml = None  # type: ignore

REQUIRED_EXISTS: tuple[str, ...] = (
    "proxies.json",
    "metadata.json",
    "artifact_manifest.json",
    "health.json",
    "base64.txt",
    "base64-dns-safe.txt",
    "base64-dns-hardened.txt",
    "proxies.txt",
    "proxies-dns-safe.txt",
    "proxies-dns-hardened.txt",
    "singbox.json",
    "singbox-dns-safe.json",
    "singbox-dns-hardened.json",
    "singbox-vpn.json",
    "singbox-vpn-dns-safe.json",
    "singbox-vpn-dns-hardened.json",
    "clash.yaml",
    "clash-dns-safe.yaml",
    "clash-dns-hardened.yaml",
    "singbox-chains.json",
    "singbox-chains-dns-safe.json",
    "singbox-chains-dns-hardened.json",
    "chains.json",
    "chains-dns-safe.json",
    "chains-dns-hardened.json",
    "side_products.zip",
    "side_products-dns-safe.zip",
    "side_products-dns-hardened.zip",
    "chosen/base64.txt",
    "chosen/base64-dns-safe.txt",
    "chosen/base64-dns-hardened.txt",
    "data/clean_ips.json",
    "data/proxy_history_viz.json",
    "data/active_proxy_trend.json",
    "data/evasion_trend.json",
    "docs/wiki/index.md",
    "index.html",
    "assets/js/runtime-config.js",
    "api/proxies",
    "api/stats",
)

REQUIRED_NONEMPTY: tuple[str, ...] = (
    "proxies.json",
    "metadata.json",
    "artifact_manifest.json",
    "health.json",
    "singbox.json",
    "singbox-dns-safe.json",
    "singbox-dns-hardened.json",
    "singbox-vpn.json",
    "singbox-vpn-dns-safe.json",
    "singbox-vpn-dns-hardened.json",
    "clash.yaml",
    "clash-dns-safe.yaml",
    "clash-dns-hardened.yaml",
    "singbox-chains.json",
    "singbox-chains-dns-safe.json",
    "singbox-chains-dns-hardened.json",
    "chains.json",
    "chains-dns-safe.json",
    "chains-dns-hardened.json",
    "side_products.zip",
    "side_products-dns-safe.zip",
    "side_products-dns-hardened.zip",
    "data/clean_ips.json",
    "data/proxy_history_viz.json",
    "data/active_proxy_trend.json",
    "data/evasion_trend.json",
    "docs/wiki/index.md",
    "index.html",
    "assets/js/runtime-config.js",
    "api/proxies",
    "api/stats",
)

JSON_FILES: tuple[str, ...] = tuple(
    name
    for name in REQUIRED_EXISTS
    if name.endswith(".json") or name in {"api/proxies", "api/stats"}
)

ZIP_FILES: tuple[str, ...] = tuple(
    name for name in REQUIRED_EXISTS if name.endswith(".zip")
)
SINGBOX_FILES: tuple[str, ...] = tuple(
    name
    for name in REQUIRED_EXISTS
    if name.startswith("singbox") and name.endswith(".json")
)
CLASH_FILES: tuple[str, ...] = tuple(
    name
    for name in REQUIRED_EXISTS
    if name.startswith("clash") and name.endswith(".yaml")
)
SING_BOX_BINARY_NAMES: tuple[str, ...] = ("sing-box", "sing-box.exe")
MIHOMO_BINARY_NAMES: tuple[str, ...] = (
    "mihomo",
    "mihomo.exe",
    "clash-meta",
    "clash-meta.exe",
    "clash",
    "clash.exe",
)
REQUIRED_ZIP_MEMBERS: dict[str, tuple[str, ...]] = {
    "side_products.zip": ("proxies.txt",),
    "side_products-dns-safe.zip": ("proxies.txt",),
    "side_products-dns-hardened.zip": ("proxies.txt",),
}

# Keep full-record validation for correctness while capping noisy output.
MAX_PROXY_VALIDATION_ERRORS = 500
ZIP_SECRET_SCAN_MAX_BYTES = 1024 * 1024
ZIP_DEPLOY_SECRET_RE = re.compile(
    r"(?im)\b(?:"
    r"ADMIN_API_KEY|CS_PUBLIC_KEY|STEGO_KEY|CONFIG_STREAM_KEY|"
    r"PINATA_JWT|HF_TOKEN|TELEGRAM_BOT_TOKEN|GDRIVE_CLIENT_SECRET|"
    r"GDRIVE_REFRESH_TOKEN|CF_TOKEN"
    r")\s*[:=]\s*[^\s#'\"]{8,}"
)
ZIP_DEPLOY_SECRET_MARKERS = (
    "PLACEHOLDER_KEY_INJECTED_BY_CI",
    "PLACEHOLDER_PUBLIC_KEY",
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = REPO_ROOT / "schema"
_MANIFEST_PRIVATE_KEY_ENV = (
    "CS_SIGNING_PRIVATE_KEY_HEX",
    "CONFIGSTREAM_SIGNING_PRIVATE_KEY_HEX",
)


def _public_key_from_runtime_env() -> ed25519.Ed25519PublicKey | None:
    value = (os.environ.get("CS_PUBLIC_KEY") or "").strip()
    if not value:
        return None
    if "PLACEHOLDER" in value or "79e/79e/" in value:
        return None
    try:
        key_bytes = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):  # type: ignore[name-defined]
        key_bytes = b""

    if key_bytes:
        try:
            parsed = serialization.load_der_public_key(key_bytes)
            if isinstance(parsed, ed25519.Ed25519PublicKey):
                return parsed
        except (ValueError, TypeError):
            pass
        try:
            return ed25519.Ed25519PublicKey.from_public_bytes(key_bytes)
        except ValueError:
            pass
    try:
        raw = bytes.fromhex(value)
    except ValueError:
        return None
    try:
        return ed25519.Ed25519PublicKey.from_public_bytes(raw)
    except ValueError:
        return None


def _manifest_signer_from_env() -> ed25519.Ed25519PrivateKey | None:
    key_hex = ""
    for env_name in _MANIFEST_PRIVATE_KEY_ENV:
        key_hex = (os.environ.get(env_name) or "").strip()
        if key_hex:
            break
    if not key_hex:
        return None
    key_bytes = bytes.fromhex(key_hex)
    if len(key_bytes) == 64:
        key_bytes = key_bytes[:32]
    if len(key_bytes) != 32:
        raise ValueError("Manifest signing key must be 32 or 64 bytes (hex).")
    return ed25519.Ed25519PrivateKey.from_private_bytes(key_bytes)


def _canonical_manifest_payload(manifest: dict[str, object]) -> bytes:
    payload = dict(manifest)
    payload.pop("manifest_signature", None)
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return canonical.encode("utf-8")


def _load_json(path: Path) -> tuple[object | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON in {path.name}: {exc}"
    except OSError as exc:
        return None, f"could not read {path.name}: {exc}"


def _load_yaml(path: Path) -> tuple[object | None, str | None]:
    if yaml is None:
        return None, "PyYAML is not available for Clash semantic validation"
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")), None
    except yaml.YAMLError as exc:  # type: ignore[attr-defined]
        return None, f"invalid YAML in {path.name}: {exc}"
    except OSError as exc:
        return None, f"could not read {path.name}: {exc}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _first_available_binary(names: tuple[str, ...]) -> str | None:
    for name in names:
        binary = shutil.which(name)
        if binary:
            return binary
    return None


def _run_native_check(command: list[str], rel_path: str) -> tuple[str, str | None]:
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "failed", f"{rel_path} native client check could not run: {exc}"
    if proc.returncode == 0:
        return "passed", None
    output = (proc.stderr or proc.stdout or "native client returned non-zero").strip()
    if len(output) > 500:
        output = output[:500] + "...[truncated]"
    return "failed", f"{rel_path} native client check failed: {output}"


def collect_native_client_report(root: Path) -> dict[str, object]:
    """Return structured optional native client check evidence."""
    generated_at = datetime.now(timezone.utc).isoformat()
    report: dict[str, object] = {
        "schema_version": 1,
        "generated_at": generated_at,
        "artifact_dir": str(root),
        "tools": {},
        "checks": [],
        "summary": {"passed": 0, "failed": 0, "skipped": 0},
    }
    tools = report["tools"]
    checks = report["checks"]
    summary = report["summary"]
    assert isinstance(tools, dict)
    assert isinstance(checks, list)
    assert isinstance(summary, dict)

    sing_box = _first_available_binary(SING_BOX_BINARY_NAMES)
    tools["sing-box"] = {"available": bool(sing_box), "binary": sing_box}
    for rel_path in SINGBOX_FILES:
        target = root / rel_path
        if not target.is_file():
            continue
        if not sing_box:
            status, error = "skipped", None
            command = None
        else:
            command = [sing_box, "check", "-c", str(target)]
            status, error = _run_native_check(command, rel_path)
        summary[status] = int(summary.get(status, 0)) + 1
        checks.append(
            {
                "core": "sing-box",
                "path": rel_path,
                "status": status,
                "command": command,
                "error": error,
            }
        )

    mihomo = _first_available_binary(MIHOMO_BINARY_NAMES)
    tools["mihomo"] = {"available": bool(mihomo), "binary": mihomo}
    for rel_path in CLASH_FILES:
        target = root / rel_path
        if not target.is_file():
            continue
        if not mihomo:
            status, error = "skipped", None
            command = None
        else:
            command = [mihomo, "-t", "-f", str(target)]
            status, error = _run_native_check(command, rel_path)
        summary[status] = int(summary.get(status, 0)) + 1
        checks.append(
            {
                "core": "clash",
                "path": rel_path,
                "status": status,
                "command": command,
                "error": error,
            }
        )

    return report


def _validate_native_clients(root: Path) -> list[str]:
    report = collect_native_client_report(root)
    checks = report.get("checks", [])
    if not isinstance(checks, list):
        return ["native client report malformed"]
    return [
        str(check["error"])
        for check in checks
        if isinstance(check, dict) and check.get("status") == "failed"
    ]


def write_native_client_report(root: Path, report_path: Path) -> None:
    """Write optional native client check evidence to *report_path*."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(collect_native_client_report(root), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


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


def _safe_join(root: Path, rel_path: str) -> Path:
    target = (root / rel_path).resolve()
    root_resolved = root.resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise ValueError(f"path escapes artifact root: {rel_path}")
    return target


def _required_schema_keys(schema_name: str) -> set[str]:
    schema_path = SCHEMA_DIR / schema_name
    payload, error = _load_json(schema_path)
    if error or not isinstance(payload, dict):
        return set()
    required = payload.get("required", [])
    return {str(item) for item in required if isinstance(item, str)}


def _schema_payload(schema_name: str) -> dict:
    payload, error = _load_json(SCHEMA_DIR / schema_name)
    if error or not isinstance(payload, dict):
        return {}
    return payload


def _type_matches(value: object, expected_type: object) -> bool:
    expected = expected_type if isinstance(expected_type, list) else [expected_type]
    for item in expected:
        if item == "null" and value is None:
            return True
        if item == "boolean" and isinstance(value, bool):
            return True
        if item == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if (
            item == "number"
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
        ):
            return True
        if item == "string" and isinstance(value, str):
            return True
        if item == "array" and isinstance(value, list):
            return True
        if item == "object" and isinstance(value, dict):
            return True
    return False


def _resolve_schema_ref(schema: dict, ref: str) -> dict:
    prefix = "#/$defs/"
    if not ref.startswith(prefix):
        return {}
    defs = schema.get("$defs", {})
    if not isinstance(defs, dict):
        return {}
    target = defs.get(ref[len(prefix) :], {})
    return target if isinstance(target, dict) else {}


def _validate_schema_rule(
    value: object, rule: dict, root_schema: dict, label: str
) -> list[str]:
    errors: list[str] = []
    ref = rule.get("$ref")
    if isinstance(ref, str):
        target = _resolve_schema_ref(root_schema, ref)
        if target:
            return _validate_schema_rule(value, target, root_schema, label)

    for branch_key in ("oneOf", "anyOf"):
        branches = rule.get(branch_key)
        if isinstance(branches, list):
            branch_errors = [
                _validate_schema_rule(value, branch, root_schema, label)
                for branch in branches
                if isinstance(branch, dict)
            ]
            if any(not branch_error for branch_error in branch_errors):
                return []
            errors.append(f"{label} does not match any allowed schema shape")
            return errors

    expected_type = rule.get("type")
    if expected_type is not None and not _type_matches(value, expected_type):
        errors.append(f"{label} has invalid type")
        return errors

    enum = rule.get("enum")
    if isinstance(enum, list) and value not in enum:
        errors.append(f"{label} has invalid value")

    pattern = rule.get("pattern")
    if isinstance(pattern, str) and isinstance(value, str):
        if not re.match(pattern, value):
            errors.append(f"{label} does not match required pattern")

    minimum = rule.get("minimum")
    if (
        isinstance(minimum, (int, float))
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value < minimum
    ):
        errors.append(f"{label} must be >= {minimum}")

    if isinstance(value, dict):
        errors.extend(_validate_dict_against_rule(value, rule, root_schema, label))
    elif isinstance(value, list):
        item_rule = rule.get("items")
        if isinstance(item_rule, dict):
            for index, item in enumerate(value):
                errors.extend(
                    _validate_schema_rule(
                        item, item_rule, root_schema, f"{label}[{index}]"
                    )
                )
    return errors


def _validate_dict_against_rule(
    value: dict, rule: dict, root_schema: dict, label: str
) -> list[str]:
    errors: list[str] = []
    required = rule.get("required", [])
    if isinstance(required, list):
        for key in sorted(str(item) for item in required if isinstance(item, str)):
            if key not in value:
                errors.append(f"{label} missing required key: {key}")

    properties = rule.get("properties", {})
    if isinstance(properties, dict):
        if rule.get("additionalProperties") is False:
            allowed = {str(key) for key in properties.keys()}
            for key in sorted(set(value.keys()) - allowed):
                errors.append(f"{label} contains unknown schema key: {key}")
        for key, nested_value in value.items():
            nested_rule = properties.get(key)
            if isinstance(nested_rule, dict):
                errors.extend(
                    _validate_schema_rule(
                        nested_value, nested_rule, root_schema, f"{label}.{key}"
                    )
                )

    additional = rule.get("additionalProperties")
    if isinstance(additional, dict) and isinstance(properties, dict):
        known = {str(key) for key in properties.keys()}
        for key, nested_value in value.items():
            if key in known:
                continue
            errors.extend(
                _validate_schema_rule(
                    nested_value, additional, root_schema, f"{label}.{key}"
                )
            )
    return errors


def _validate_conditional_schema(
    payload: dict, schema: dict, file_name: str
) -> list[str]:
    errors: list[str] = []
    clauses = schema.get("allOf", [])
    if not isinstance(clauses, list):
        return errors
    for clause in clauses:
        if not isinstance(clause, dict):
            continue
        condition = clause.get("if")
        then = clause.get("then")
        if not isinstance(condition, dict) or not isinstance(then, dict):
            continue
        if not _schema_condition_matches(payload, condition):
            continue
        errors.extend(_validate_dict_against_rule(payload, then, schema, file_name))
    return errors


def _schema_condition_matches(payload: dict, condition: dict) -> bool:
    required = condition.get("required", [])
    if isinstance(required, list):
        for key in required:
            if isinstance(key, str) and key not in payload:
                return False
    properties = condition.get("properties", {})
    if not isinstance(properties, dict):
        return True
    for key, rule in properties.items():
        if key not in payload or not isinstance(rule, dict):
            continue
        if "const" in rule and payload[key] != rule["const"]:
            return False
        enum = rule.get("enum")
        if isinstance(enum, list) and payload[key] not in enum:
            return False
    return True


def _validate_schema_object(
    payload: object, schema_name: str, file_name: str
) -> list[str]:
    errors = _validate_required_keys(payload, schema_name, file_name)
    if not isinstance(payload, dict):
        return errors
    schema = _schema_payload(schema_name)
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return errors

    if schema.get("additionalProperties") is False:
        allowed = {str(key) for key in properties.keys()}
        for key in sorted(set(payload.keys()) - allowed):
            errors.append(f"{file_name} contains unknown schema key: {key}")

    for key, value in payload.items():
        rule = properties.get(key)
        if isinstance(rule, dict):
            errors.extend(
                _validate_schema_rule(value, rule, schema, f"{file_name} {key}")
            )
    errors.extend(_validate_conditional_schema(payload, schema, file_name))
    return errors


def _validate_required_keys(
    payload: object, schema_name: str, file_name: str
) -> list[str]:
    if not isinstance(payload, dict):
        return [f"{file_name} must be a JSON object"]
    errors: list[str] = []
    for key in sorted(_required_schema_keys(schema_name) - set(payload.keys())):
        errors.append(f"{file_name} missing required key from schema: {key}")
    return errors


def _validate_manifest(root: Path, manifest: object) -> list[str]:
    errors = _validate_schema_object(
        manifest, "artifact_manifest.schema.json", "artifact_manifest.json"
    )
    if not isinstance(manifest, dict):
        return errors

    files = manifest.get("files")
    if not isinstance(files, list):
        return errors + ["artifact_manifest.json missing files list"]

    manifest_paths: set[str] = set()
    for index, item in enumerate(files):
        if not isinstance(item, dict):
            errors.append(f"artifact_manifest.json files[{index}] must be an object")
            continue
        rel_path = item.get("path")
        if not isinstance(rel_path, str) or not rel_path:
            errors.append(f"artifact_manifest.json files[{index}] missing path")
            continue
        manifest_paths.add(rel_path)
        try:
            target = _safe_join(root, rel_path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not target.is_file():
            errors.append(f"artifact_manifest.json references missing file: {rel_path}")
            continue
        actual_size = target.stat().st_size
        if item.get("size_bytes") != actual_size:
            errors.append(f"artifact_manifest.json size mismatch: {rel_path}")
        actual_hash = _sha256(target)
        if item.get("sha256") != actual_hash:
            errors.append(f"artifact_manifest.json sha256 mismatch: {rel_path}")

    for rel_path in REQUIRED_EXISTS:
        if rel_path == "artifact_manifest.json":
            continue
        if rel_path not in manifest_paths:
            errors.append(f"artifact_manifest.json missing file entry: {rel_path}")

    if isinstance(manifest.get("file_count"), int) and manifest["file_count"] != len(
        files
    ):
        errors.append("artifact_manifest.json file_count does not match files length")
    if isinstance(manifest.get("total_size_bytes"), int) and manifest[
        "total_size_bytes"
    ] != sum(
        (root / str(item.get("path"))).stat().st_size
        for item in files
        if isinstance(item, dict)
        and isinstance(item.get("path"), str)
        and (root / str(item.get("path"))).is_file()
    ):
        errors.append("artifact_manifest.json total_size_bytes does not match files")

    errors.extend(_validate_manifest_signature(manifest))
    return errors


def _validate_manifest_signature(manifest: dict[str, object]) -> list[str]:
    errors: list[str] = []
    signature_obj = manifest.get("manifest_signature")
    verifier_key = _public_key_from_runtime_env()

    if signature_obj is None:
        if verifier_key is not None:
            errors.append(
                "artifact_manifest.json missing manifest_signature while CS_PUBLIC_KEY is configured"
            )
        return errors

    if not isinstance(signature_obj, dict):
        errors.append("artifact_manifest.json manifest_signature must be an object")
        return errors

    algorithm = signature_obj.get("algorithm")
    signature_hex = signature_obj.get("signature")
    if algorithm != "ed25519":
        errors.append(
            "artifact_manifest.json manifest_signature.algorithm must be ed25519"
        )
        return errors
    if not isinstance(signature_hex, str) or not re.fullmatch(
        r"[a-f0-9]{128}", signature_hex
    ):
        errors.append(
            "artifact_manifest.json manifest_signature.signature must be 128-char lowercase hex"
        )
        return errors

    if verifier_key is None:
        return errors

    try:
        verifier_key.verify(
            bytes.fromhex(signature_hex), _canonical_manifest_payload(manifest)
        )
    except (InvalidSignature, ValueError):
        errors.append("artifact_manifest.json manifest_signature verification failed")
    return errors


def _validate_health(health: object) -> list[str]:
    errors = _validate_schema_object(health, "health.schema.json", "health.json")
    if not isinstance(health, dict):
        return errors
    if health.get("status") not in {"ok", "degraded"}:
        errors.append("health.json status must be 'ok' or 'degraded'")
    for key in ("total_working", "total_tested"):
        if not isinstance(health.get(key), int) or health[key] < 0:
            errors.append(f"health.json {key} must be a non-negative integer")
    if not isinstance(health.get("notes"), list):
        errors.append("health.json notes must be a list")
    return errors


def _validate_metadata(metadata: object) -> list[str]:
    errors = _validate_schema_object(metadata, "metadata.schema.json", "metadata.json")
    if not isinstance(metadata, dict):
        return errors
    for key in ("total_working", "total_tested", "total_proxies"):
        if not isinstance(metadata.get(key), int) or metadata[key] < 0:
            errors.append(f"metadata.json {key} must be a non-negative integer")
    success_rate = metadata.get("success_rate")
    if not isinstance(success_rate, (int, float)) or success_rate < 0:
        errors.append("metadata.json success_rate must be a non-negative number")
    return errors


def _validate_proxies(payload: object, file_name: str) -> list[str]:
    if not isinstance(payload, list):
        return [f"{file_name} must be a JSON array"]
    errors: list[str] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            errors.append(f"{file_name}[{index}] must be an object")
            if len(errors) >= MAX_PROXY_VALIDATION_ERRORS:
                errors.append(
                    f"{file_name} validation stopped after {MAX_PROXY_VALIDATION_ERRORS} errors"
                )
                break
            continue
        missing = _required_schema_keys("proxy.schema.json") - set(item.keys())
        if missing:
            errors.append(
                f"{file_name}[{index}] missing required proxy keys: "
                f"{', '.join(sorted(missing))}"
            )
        errors.extend(
            _validate_schema_object(item, "proxy.schema.json", f"{file_name}[{index}]")
        )
        if len(errors) >= MAX_PROXY_VALIDATION_ERRORS:
            errors.append(
                f"{file_name} validation stopped after {MAX_PROXY_VALIDATION_ERRORS} errors"
            )
            break
    return errors


def _validate_singbox_config(payload: object, file_name: str) -> list[str]:
    if not isinstance(payload, dict):
        return [f"{file_name} must be a JSON object"]
    outbounds = payload.get("outbounds")
    if not isinstance(outbounds, list) or not outbounds:
        return [f"{file_name} outbounds must be a non-empty list"]
    errors: list[str] = []
    tags: set[str] = set()
    for index, outbound in enumerate(outbounds):
        if not isinstance(outbound, dict):
            errors.append(f"{file_name} outbounds[{index}] must be an object")
            continue
        outbound_type = outbound.get("type")
        tag = outbound.get("tag")
        if not isinstance(outbound_type, str) or not outbound_type:
            errors.append(f"{file_name} outbounds[{index}] missing type")
        if not isinstance(tag, str) or not tag:
            errors.append(f"{file_name} outbounds[{index}] missing tag")
            continue
        if tag in tags:
            errors.append(f"{file_name} duplicate outbound tag: {tag}")
        tags.add(tag)

    for index, outbound in enumerate(outbounds):
        if not isinstance(outbound, dict):
            continue
        outbound_type = outbound.get("type")
        detour = outbound.get("detour")
        if detour is not None:
            if not isinstance(detour, str) or not detour:
                errors.append(f"{file_name} outbounds[{index}] has invalid detour")
            elif detour not in tags:
                errors.append(f"{file_name} unknown outbound detour: {detour}")
        if outbound_type not in {"selector", "urltest"}:
            continue
        refs = outbound.get("outbounds")
        if not isinstance(refs, list):
            errors.append(f"{file_name} outbounds[{index}] missing outbound references")
            continue
        for ref in refs:
            if not isinstance(ref, str) or not ref:
                errors.append(f"{file_name} outbounds[{index}] has invalid reference")
            elif ref not in tags:
                errors.append(f"{file_name} unknown outbound reference: {ref}")

    route = payload.get("route")
    if isinstance(route, dict):
        rules = route.get("rules")
        if isinstance(rules, list):
            for index, rule in enumerate(rules):
                if not isinstance(rule, dict):
                    continue
                ref = rule.get("outbound")
                if ref is None:
                    continue
                if not isinstance(ref, str) or not ref:
                    errors.append(
                        f"{file_name} route.rules[{index}] has invalid outbound"
                    )
                elif ref not in tags:
                    errors.append(f"{file_name} unknown route outbound: {ref}")

    dns = payload.get("dns")
    if isinstance(dns, dict):
        servers = dns.get("servers")
        if isinstance(servers, list):
            for index, server in enumerate(servers):
                if not isinstance(server, dict):
                    continue
                detour = server.get("detour")
                if detour is None:
                    continue
                if not isinstance(detour, str) or not detour:
                    errors.append(
                        f"{file_name} dns.servers[{index}] has invalid detour"
                    )
                elif detour not in tags:
                    errors.append(f"{file_name} unknown DNS detour: {detour}")
    return errors


def _validate_clash_config(payload: object, file_name: str) -> list[str]:
    if not isinstance(payload, dict):
        return [f"{file_name} must be a YAML object"]
    proxies = payload.get("proxies")
    groups = payload.get("proxy-groups")
    rules = payload.get("rules")
    errors: list[str] = []
    if not isinstance(proxies, list):
        errors.append(f"{file_name} proxies must be a list")
        proxies = []
    if not isinstance(groups, list) or not groups:
        errors.append(f"{file_name} proxy-groups must be a non-empty list")
        groups = []
    if not isinstance(rules, list) or not rules:
        errors.append(f"{file_name} rules must be a non-empty list")

    names: set[str] = {"DIRECT", "REJECT", "GLOBAL"}
    for index, proxy in enumerate(proxies):
        if not isinstance(proxy, dict):
            errors.append(f"{file_name} proxies[{index}] must be an object")
            continue
        name = proxy.get("name")
        proxy_type = proxy.get("type")
        if not isinstance(name, str) or not name:
            errors.append(f"{file_name} proxies[{index}] missing name")
            continue
        if name in names:
            errors.append(f"{file_name} duplicate proxy/group name: {name}")
        names.add(name)
        if not isinstance(proxy_type, str) or not proxy_type:
            errors.append(f"{file_name} proxies[{index}] missing type")

    group_refs: list[tuple[int, str]] = []
    for index, group in enumerate(groups):
        if not isinstance(group, dict):
            errors.append(f"{file_name} proxy-groups[{index}] must be an object")
            continue
        name = group.get("name")
        group_type = group.get("type")
        refs = group.get("proxies")
        if not isinstance(name, str) or not name:
            errors.append(f"{file_name} proxy-groups[{index}] missing name")
        else:
            if name in names:
                errors.append(f"{file_name} duplicate proxy/group name: {name}")
            names.add(name)
        if not isinstance(group_type, str) or not group_type:
            errors.append(f"{file_name} proxy-groups[{index}] missing type")
        if not isinstance(refs, list) or not refs:
            errors.append(
                f"{file_name} proxy-groups[{index}] proxies must be non-empty"
            )
            continue
        for ref in refs:
            if isinstance(ref, str) and ref:
                group_refs.append((index, ref))
            else:
                errors.append(
                    f"{file_name} proxy-groups[{index}] has invalid reference"
                )

    for index, ref in group_refs:
        if ref not in names:
            errors.append(f"{file_name} proxy-groups[{index}] unknown reference: {ref}")

    if isinstance(rules, list):
        for index, rule in enumerate(rules):
            if not isinstance(rule, str):
                errors.append(f"{file_name} rules[{index}] must be a string")
                continue
            parts = [part.strip() for part in rule.split(",")]
            if len(parts) < 2:
                continue
            policy = parts[-1]
            if policy and policy not in names:
                errors.append(f"{file_name} rules[{index}] unknown policy: {policy}")
    return errors


def _validate_api_alias_parity(root: Path) -> list[str]:
    errors: list[str] = []
    for canonical, alias in (
        ("proxies.json", "api/proxies"),
        ("metadata.json", "api/stats"),
    ):
        canonical_path = root / canonical
        alias_path = root / alias
        if not canonical_path.is_file() or not alias_path.is_file():
            continue
        if _sha256(canonical_path) != _sha256(alias_path):
            errors.append(f"{alias} must match {canonical}")
    return errors


def _validate_categorized_lists(root: Path) -> list[str]:
    """Validate all country and protocol specific proxy list JSON files."""
    errors: list[str] = []
    # Countries
    country_dir = root / "countries"
    if country_dir.is_dir():
        for path in country_dir.glob("*.list.json"):
            payload, error = _load_json(path)
            if error:
                errors.append(error)
            elif isinstance(payload, list):
                errors.extend(_validate_proxies(payload, f"countries/{path.name}"))
            else:
                errors.append(f"countries/{path.name} must be a JSON array")

    # Protocols
    proto_dir = root / "protocols"
    if proto_dir.is_dir():
        for path in proto_dir.glob("*.list.json"):
            payload, error = _load_json(path)
            if error:
                errors.append(error)
            elif isinstance(payload, list):
                errors.extend(_validate_proxies(payload, f"protocols/{path.name}"))
            else:
                errors.append(f"protocols/{path.name} must be a JSON array")
    return errors


def _validate_zip_members(rel_path: str, archive: zipfile.ZipFile) -> list[str]:
    errors: list[str] = []
    names = set(archive.namelist())
    for member in REQUIRED_ZIP_MEMBERS.get(rel_path, ()):
        if member not in names:
            errors.append(f"{rel_path} missing ZIP member: {member}")
    for name in sorted(names):
        normalized = name.replace("\\", "/")
        parts = [part for part in normalized.split("/") if part]
        if (
            not normalized
            or normalized.startswith("/")
            or normalized.startswith("../")
            or "/../" in normalized
            or ".." in parts
            or ":" in parts[0]
        ):
            errors.append(f"{rel_path} contains unsafe ZIP member path: {name}")
            continue
        if name.endswith("/"):
            continue
        try:
            with archive.open(name, "r") as member_file:
                chunk = member_file.read(ZIP_SECRET_SCAN_MAX_BYTES + 1)
        except (KeyError, OSError, RuntimeError, zipfile.BadZipFile) as exc:
            errors.append(f"{rel_path} could not read ZIP member {name}: {exc}")
            continue
        text = chunk[:ZIP_SECRET_SCAN_MAX_BYTES].decode("utf-8", errors="ignore")
        if any(marker in text for marker in ZIP_DEPLOY_SECRET_MARKERS):
            errors.append(f"{rel_path} ZIP member leaks deploy secret marker: {name}")
        if ZIP_DEPLOY_SECRET_RE.search(text):
            errors.append(
                f"{rel_path} ZIP member leaks deploy secret assignment: {name}"
            )
    return errors


def write_pages_contract(root: Path) -> None:
    metadata, _ = _load_json(root / "metadata.json")
    metadata_obj = metadata if isinstance(metadata, dict) else {}
    generated_at = str(
        metadata_obj.get("generated_at")
        or metadata_obj.get("last_updated_utc")
        or datetime.now(timezone.utc).isoformat()
    )
    trace_id = str(metadata_obj.get("trace_id") or "-")
    total_working = int(metadata_obj.get("total_working", 0) or 0)
    total_tested = int(metadata_obj.get("total_tested", 0) or 0)

    health: dict[str, object] = {
        "schema_version": "1.0",
        "status": "degraded" if total_working == 0 else "ok",
        "generated_at": generated_at,
        "trace_id": trace_id,
        "source_commit": os.environ.get("GITHUB_SHA", ""),
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        "total_working": total_working,
        "total_tested": total_tested,
        "schema_validated": True,
        "notes": [],
    }
    (root / "health.json").write_text(
        json.dumps(health, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    files: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(root).as_posix()
        if rel_path == "artifact_manifest.json" or rel_path.endswith(".tmp"):
            continue
        files.append(
            {
                "path": rel_path,
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
                "category": _artifact_category(rel_path),
            }
        )

    manifest: dict[str, object] = {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "artifact_generated_at": generated_at,
        "trace_id": trace_id,
        "source_commit": os.environ.get("GITHUB_SHA", ""),
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        "file_count": len(files),
        "total_size_bytes": sum(cast(int, item["size_bytes"]) for item in files),
        "files": files,
    }
    signer = _manifest_signer_from_env()
    if signer is not None:
        payload = _canonical_manifest_payload(manifest)
        signature = signer.sign(payload).hex()
        public_key = signer.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        key_id = hashlib.sha256(public_key).hexdigest()[:16]
        manifest["manifest_signature"] = {
            "algorithm": "ed25519",
            "signature": signature,
            "key_id": f"sha256:{key_id}",
        }
    (root / "artifact_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def validate_pages_artifact(
    root: Path, *, native_client_check: bool = False
) -> list[str]:
    errors: list[str] = []
    if not root.exists():
        return [f"artifact directory does not exist: {root}"]
    if not root.is_dir():
        return [f"artifact path is not a directory: {root}"]

    for rel_path in REQUIRED_EXISTS:
        try:
            target = _safe_join(root, rel_path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not target.is_file():
            errors.append(f"missing required file: {rel_path}")

    for rel_path in REQUIRED_NONEMPTY:
        try:
            target = _safe_join(root, rel_path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if target.is_file() and target.stat().st_size <= 0:
            errors.append(f"required file is empty: {rel_path}")

    for rel_path in JSON_FILES:
        try:
            target = _safe_join(root, rel_path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not target.is_file():
            continue
        _, error = _load_json(target)
        if error:
            errors.append(error.replace(target.name, rel_path, 1))

    for rel_path in ZIP_FILES:
        try:
            target = _safe_join(root, rel_path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not target.is_file():
            continue
        try:
            with zipfile.ZipFile(target, "r") as archive:
                bad_member = archive.testzip()
                errors.extend(_validate_zip_members(rel_path, archive))
        except zipfile.BadZipFile as exc:
            errors.append(f"invalid ZIP in {rel_path}: {exc}")
            continue
        if bad_member:
            errors.append(f"corrupt ZIP member in {rel_path}: {bad_member}")

    for rel_path in SINGBOX_FILES:
        target = root / rel_path
        if not target.is_file():
            continue
        payload, error = _load_json(target)
        if error:
            continue
        errors.extend(_validate_singbox_config(payload, rel_path))

    for rel_path in CLASH_FILES:
        target = root / rel_path
        if not target.is_file():
            continue
        payload, error = _load_yaml(target)
        if error:
            errors.append(error.replace(target.name, rel_path, 1))
            continue
        errors.extend(_validate_clash_config(payload, rel_path))

    manifest_path = root / "artifact_manifest.json"
    if manifest_path.is_file():
        manifest, error = _load_json(manifest_path)
        if error:
            errors.append(error)
        else:
            errors.extend(_validate_manifest(root, manifest))

    health_path = root / "health.json"
    if health_path.is_file():
        health, error = _load_json(health_path)
        if error:
            errors.append(error)
        else:
            errors.extend(_validate_health(health))

    metadata_path = root / "metadata.json"
    if metadata_path.is_file():
        metadata, error = _load_json(metadata_path)
        if not error:
            errors.extend(_validate_metadata(metadata))

    proxies_path = root / "proxies.json"
    if proxies_path.is_file():
        proxies, error = _load_json(proxies_path)
        if not error:
            errors.extend(_validate_proxies(proxies, "proxies.json"))

    api_proxies_path = root / "api" / "proxies"
    if api_proxies_path.is_file():
        api_proxies, error = _load_json(api_proxies_path)
        if not error:
            errors.extend(_validate_proxies(api_proxies, "api/proxies"))

    errors.extend(_validate_categorized_lists(root))
    errors.extend(_validate_api_alias_parity(root))
    if native_client_check:
        errors.extend(_validate_native_clients(root))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh-contract",
        action="store_true",
        help="Rewrite health.json and artifact_manifest.json before validation.",
    )
    parser.add_argument(
        "--native-client-check",
        action="store_true",
        help=(
            "Also run local sing-box/mihomo config checks when those binaries are "
            "available. Missing binaries are treated as a skip."
        ),
    )
    parser.add_argument(
        "--native-report-file",
        type=Path,
        help=(
            "Write structured native client check evidence. Missing binaries are "
            "recorded as skipped checks."
        ),
    )
    parser.add_argument("artifact_dir", type=Path, help="Prepared Pages output dir")
    args = parser.parse_args()

    if args.refresh_contract:
        write_pages_contract(args.artifact_dir)

    errors = validate_pages_artifact(
        args.artifact_dir, native_client_check=args.native_client_check
    )
    if args.native_report_file:
        write_native_client_report(args.artifact_dir, args.native_report_file)
    if errors:
        print("ERROR: Pages artifact validation failed")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"OK: Pages artifact validation passed for {args.artifact_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
