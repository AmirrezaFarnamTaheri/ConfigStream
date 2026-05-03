# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate the static GitHub Pages artifact before deployment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

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

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = REPO_ROOT / "schema"


def _load_json(path: Path) -> tuple[object | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON in {path.name}: {exc}"
    except OSError as exc:
        return None, f"could not read {path.name}: {exc}"


def _sha256(path: Path) -> str:
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
    errors = _validate_required_keys(
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

    return errors


def _validate_health(health: object) -> list[str]:
    errors = _validate_required_keys(health, "health.schema.json", "health.json")
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
    errors = _validate_required_keys(metadata, "metadata.schema.json", "metadata.json")
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
    for index, item in enumerate(payload[:50]):
        if not isinstance(item, dict):
            errors.append(f"{file_name}[{index}] must be an object")
            continue
        missing = _required_schema_keys("proxy.schema.json") - set(item.keys())
        if missing:
            errors.append(
                f"{file_name}[{index}] missing required proxy keys: "
                f"{', '.join(sorted(missing))}"
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

    health = {
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

    manifest = {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "artifact_generated_at": generated_at,
        "trace_id": trace_id,
        "source_commit": os.environ.get("GITHUB_SHA", ""),
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        "file_count": len(files),
        "total_size_bytes": sum(int(item["size_bytes"]) for item in files),
        "files": files,
    }
    (root / "artifact_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def validate_pages_artifact(root: Path) -> list[str]:
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
        except zipfile.BadZipFile as exc:
            errors.append(f"invalid ZIP in {rel_path}: {exc}")
            continue
        if bad_member:
            errors.append(f"corrupt ZIP member in {rel_path}: {bad_member}")

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

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh-contract",
        action="store_true",
        help="Rewrite health.json and artifact_manifest.json before validation.",
    )
    parser.add_argument("artifact_dir", type=Path, help="Prepared Pages output dir")
    args = parser.parse_args()

    if args.refresh_contract:
        write_pages_contract(args.artifact_dir)

    errors = validate_pages_artifact(args.artifact_dir)
    if errors:
        print("ERROR: Pages artifact validation failed")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"OK: Pages artifact validation passed for {args.artifact_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
