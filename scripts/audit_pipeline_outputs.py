# SPDX-License-Identifier: AGPL-3.0-or-later
"""Forensic audit helper for pipeline output artifacts."""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import shutil
import stat
import subprocess
import tempfile
import zipfile
import zlib
from pathlib import Path, PurePosixPath
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from configstream.stego import StegoPacker

MAX_ARCHIVE_FILES = 20_000
MAX_ARCHIVE_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_ARCHIVE_FILE_BYTES = 512 * 1024 * 1024
_COPY_CHUNK_BYTES = 1024 * 1024


def _which_sing_box() -> str | None:
    for name in ("sing-box", "sing-box.exe"):
        path = shutil.which(name)
        if path:
            return path
    return None


def _safe_zip_member_path(info: zipfile.ZipInfo, workdir: Path) -> Path:
    """Return a contained extraction path or reject an unsafe ZIP member."""
    name = info.filename
    if not name or "\x00" in name or "\\" in name:
        raise ValueError("ZIP contains an invalid member name")

    member = PurePosixPath(name)
    if member.is_absolute() or any(part in {"", ".", ".."} for part in member.parts):
        raise ValueError(f"ZIP member escapes extraction root: {name!r}")
    if member.parts and ":" in member.parts[0]:
        raise ValueError(f"ZIP member contains a drive-qualified path: {name!r}")

    unix_mode = (info.external_attr >> 16) & 0xFFFF
    file_type = stat.S_IFMT(unix_mode)
    if file_type == stat.S_IFLNK:
        raise ValueError(f"ZIP symbolic links are not accepted: {name!r}")
    if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
        raise ValueError(f"ZIP contains an unsupported special file: {name!r}")
    if info.flag_bits & 0x1:
        raise ValueError(f"Encrypted ZIP members are not accepted: {name!r}")
    if info.file_size < 0 or info.file_size > MAX_ARCHIVE_FILE_BYTES:
        raise ValueError(f"ZIP member exceeds the per-file size limit: {name!r}")

    root = workdir.resolve()
    target = (root / Path(*member.parts)).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"ZIP member escapes extraction root: {name!r}") from exc
    return target


def _extract_zip_safely(artifact: Path, workdir: Path) -> None:
    """Extract a ZIP only after validating all paths and expansion limits."""
    with zipfile.ZipFile(artifact, "r") as archive:
        members = archive.infolist()
        if len(members) > MAX_ARCHIVE_FILES:
            raise ValueError("ZIP contains too many members")

        planned: list[tuple[zipfile.ZipInfo, Path]] = []
        total_size = 0
        for info in members:
            target = _safe_zip_member_path(info, workdir)
            total_size += info.file_size
            if total_size > MAX_ARCHIVE_TOTAL_BYTES:
                raise ValueError("ZIP exceeds the total expanded-size limit")
            planned.append((info, target))

        for info, target in planned:
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            written = 0
            with archive.open(info, "r") as source, target.open("xb") as destination:
                while True:
                    chunk = source.read(_COPY_CHUNK_BYTES)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > info.file_size or written > MAX_ARCHIVE_FILE_BYTES:
                        raise ValueError(
                            f"ZIP member expanded beyond its declared size: {info.filename!r}"
                        )
                    destination.write(chunk)
            if written != info.file_size:
                raise ValueError(
                    f"ZIP member size mismatch after extraction: {info.filename!r}"
                )


def _extract_artifact(artifact: Path, workdir: Path) -> Path:
    if artifact.is_dir():
        return artifact.resolve()

    suffix = artifact.suffix.lower()
    if suffix == ".zip":
        _extract_zip_safely(artifact, workdir)
        return workdir
    if suffix == ".rar":
        raise RuntimeError(
            "RAR artifacts are not accepted because external extractors cannot "
            "guarantee path containment; provide a ZIP or extracted directory"
        )
    raise RuntimeError(f"Unsupported artifact type: {artifact}")


def _validate_json(path: Path, sing_box_bin: str | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "json_valid": False,
        "sing_box_check": None,
    }
    try:
        json.loads(path.read_text(encoding="utf-8"))
        result["json_valid"] = True
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        result["error"] = f"json: {type(exc).__name__}"
        return result

    if sing_box_bin:
        proc = subprocess.run(
            [sing_box_bin, "check", "-c", str(path)],
            text=True,
            capture_output=True,
            check=False,
        )
        result["sing_box_check"] = proc.returncode == 0
        if proc.returncode != 0:
            result["sing_box_error"] = (proc.stderr or proc.stdout).strip()[:2000]
    return result


def _validate_base64_file(path: Path) -> dict[str, Any]:
    ok = 0
    bad = 0
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            base64.b64decode(text, validate=True)
            ok += 1
        except (binascii.Error, ValueError):
            bad += 1
    return {"path": str(path), "valid_lines": ok, "invalid_lines": bad}


def _extract_stego(path: Path, secret_key: str | None) -> dict[str, Any]:
    result: dict[str, Any] = {"path": str(path), "decoded": False}
    if not secret_key:
        result["error"] = "STEGO_KEY/CONFIG_STREAM_KEY not provided"
        return result
    try:
        key = secret_key.encode("ascii")
        Fernet(key)
        payload = StegoPacker(key).unpack(path)
        if payload is None:
            result["error"] = "stego unpack returned None"
            return result
        json.loads(payload)
        result["decoded"] = True
        result["payload_bytes"] = len(payload.encode("utf-8"))
        return result
    except (
        OSError,
        UnicodeEncodeError,
        UnicodeDecodeError,
        ValueError,
        InvalidToken,
        json.JSONDecodeError,
        zlib.error,
    ) as exc:
        result["error"] = type(exc).__name__
        return result


def audit_artifact(
    artifact: Path,
    secret_key: str | None = None,
    contract: str = "runtime",
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "artifact": str(artifact),
        "json_configs": [],
        "base64_lists": [],
        "stego_assets": [],
        "missing_expected": [],
    }
    sing_box_bin = _which_sing_box()
    report["sing_box_binary"] = sing_box_bin

    with tempfile.TemporaryDirectory(prefix="configstream-audit-") as temp_dir:
        extracted = _extract_artifact(artifact, Path(temp_dir))

        json_files: tuple[str, ...]
        base64_files: tuple[str, ...]
        zip_files: tuple[str, ...]
        if contract == "pages":
            json_files = (
                "singbox.json",
                "singbox-dns-safe.json",
                "singbox-dns-hardened.json",
                "singbox-vpn.json",
                "singbox-vpn-dns-safe.json",
                "singbox-vpn-dns-hardened.json",
                "singbox-chains.json",
                "singbox-chains-dns-safe.json",
                "singbox-chains-dns-hardened.json",
                "chains.json",
                "chains-dns-safe.json",
                "chains-dns-hardened.json",
                "proxies.json",
                "metadata.json",
                "data/clean_ips.json",
                "data/proxy_history_viz.json",
                "data/active_proxy_trend.json",
                "data/evasion_trend.json",
            )
            base64_files = (
                "base64.txt",
                "base64-dns-safe.txt",
                "base64-dns-hardened.txt",
                "chosen/base64.txt",
                "chosen/base64-dns-safe.txt",
                "chosen/base64-dns-hardened.txt",
                "proxies.txt",
                "proxies-dns-safe.txt",
                "proxies-dns-hardened.txt",
            )
            zip_files = (
                "side_products.zip",
                "side_products-dns-safe.zip",
                "side_products-dns-hardened.zip",
            )
        else:
            json_files = (
                "singbox-dns-hardened.json",
                "singbox-dns-safe.json",
                "singbox-vpn.json",
            )
            base64_files = ("base64-dns-hardened.txt",)
            zip_files = ()

        for name in json_files:
            target = extracted / name
            if target.exists():
                report["json_configs"].append(_validate_json(target, sing_box_bin))
            else:
                report["missing_expected"].append(name)

        for name in base64_files:
            target = extracted / name
            if target.exists():
                report["base64_lists"].append(_validate_base64_file(target))
            else:
                report["missing_expected"].append(name)

        for name in zip_files:
            target = extracted / name
            if not target.exists():
                report["missing_expected"].append(name)

        for name in ("stealth_apple-touch-icon.png",):
            target = extracted / name
            if target.exists():
                report["stego_assets"].append(_extract_stego(target, secret_key))
            else:
                report["missing_expected"].append(name)

    return report


def report_has_failures(
    report: dict[str, Any], *, strict_stego_key: bool = False
) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    missing = report.get("missing_expected")
    if isinstance(missing, list) and missing:
        reasons.append(
            f"missing expected outputs: {', '.join(sorted(map(str, missing)))}"
        )

    json_configs = report.get("json_configs") or []
    if not json_configs:
        reasons.append("no JSON config outputs were audited")
    for item in json_configs:
        path = str(item.get("path", "unknown"))
        if not item.get("json_valid", False):
            reasons.append(f"{path}: invalid JSON")
        singbox_check = item.get("sing_box_check")
        if singbox_check is False:
            reasons.append(f"{path}: sing-box check failed")

    for item in report.get("base64_lists") or []:
        path = str(item.get("path", "unknown"))
        invalid = int(item.get("invalid_lines", 0) or 0)
        if invalid > 0:
            reasons.append(f"{path}: {invalid} invalid base64 lines")

    for item in report.get("stego_assets") or []:
        path = str(item.get("path", "unknown"))
        if item.get("decoded", False):
            continue
        error = str(item.get("error", "") or "")
        if "not provided" in error and not strict_stego_key:
            continue
        reasons.append(f"{path}: stego decode failed ({error or 'unknown error'})")

    return (len(reasons) > 0, reasons)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit a pipeline output artifact (ZIP or extracted directory)."
    )
    parser.add_argument(
        "--artifact",
        default="pipeline-output.zip",
        help="Artifact path (.zip or extracted directory).",
    )
    parser.add_argument(
        "--stego-key",
        default=os.getenv("STEGO_KEY") or os.getenv("CONFIG_STREAM_KEY"),
        help="Stego Fernet key (defaults to STEGO_KEY/CONFIG_STREAM_KEY env).",
    )
    parser.add_argument(
        "--report",
        default="",
        help="Optional path to write JSON report.",
    )
    parser.add_argument(
        "--contract",
        choices=["runtime", "pages"],
        default="runtime",
        help="Validation contract mode",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero status when audit failures are detected.",
    )
    parser.add_argument(
        "--strict-stego-key",
        action="store_true",
        help="In strict mode, also fail when stego key is missing.",
    )
    args = parser.parse_args()

    artifact = Path(args.artifact)
    if not artifact.exists():
        raise SystemExit(f"Artifact not found: {artifact}")

    report = audit_artifact(artifact, args.stego_key, contract=args.contract)
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    print(rendered)
    if args.report:
        Path(args.report).write_text(rendered, encoding="utf-8")
    if args.strict:
        failed, reasons = report_has_failures(
            report, strict_stego_key=bool(args.strict_stego_key)
        )
        if failed:
            raise SystemExit("Audit failed: " + "; ".join(reasons))


if __name__ == "__main__":
    main()
