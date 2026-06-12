# SPDX-License-Identifier: AGPL-3.0-or-later
"""Forensic audit helper for pipeline output artifacts."""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess  # nosec B404
import tempfile
from pathlib import Path
from typing import Any
import zipfile

from cryptography.fernet import Fernet

from configstream.stego import StegoPacker


def _which_sing_box() -> str | None:
    for name in ("sing-box", "sing-box.exe"):
        p = shutil.which(name)
        if p:
            return p
    return None


def _extract_artifact(artifact: Path, workdir: Path) -> Path:
    if artifact.is_dir():
        return artifact

    if artifact.suffix.lower() == ".zip":
        with zipfile.ZipFile(artifact, "r") as zf:
            zf.extractall(workdir)
        return workdir

    if artifact.suffix.lower() == ".rar":
        seven_zip = shutil.which("7z") or shutil.which("7z.exe")
        unrar = shutil.which("unrar")
        if seven_zip:
            subprocess.run(  # nosec B603
                [seven_zip, "x", "-y", str(artifact), f"-o{workdir}"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return workdir
        if unrar:
            subprocess.run(  # nosec B603
                [unrar, "x", "-y", str(artifact), str(workdir)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return workdir
        raise RuntimeError("RAR extraction requires 7z or unrar in PATH")

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
    except Exception as exc:
        result["error"] = f"json: {exc}"
        return result

    if sing_box_bin:
        proc = subprocess.run(  # nosec B603
            [sing_box_bin, "check", "-c", str(path)],
            text=True,
            capture_output=True,
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
        except Exception:
            bad += 1
    return {"path": str(path), "valid_lines": ok, "invalid_lines": bad}


def _extract_stego(path: Path, secret_key: str | None) -> dict[str, Any]:
    result: dict[str, Any] = {"path": str(path), "decoded": False}
    if not secret_key:
        result["error"] = "STEGO_KEY/CONFIG_STREAM_KEY not provided"
        return result
    try:
        key = secret_key.encode("utf-8")
        Fernet(key)  # validate
        payload = StegoPacker(key).unpack(path)
        if payload is None:
            result["error"] = "stego unpack returned None"
            return result
        json.loads(payload)
        result["decoded"] = True
        result["payload_bytes"] = len(payload.encode("utf-8"))
        return result
    except Exception as exc:
        result["error"] = str(exc)
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

    with tempfile.TemporaryDirectory(prefix="configstream-audit-") as td:
        extracted = _extract_artifact(artifact, Path(td))

        json_files: tuple[str, ...] = ()
        base64_files: tuple[str, ...] = ()
        zip_files: tuple[str, ...] = ()
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
            # could add zip verification here if desired

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
        description="Audit pipeline output artifact (rar/zip/dir)."
    )
    parser.add_argument(
        "--artifact",
        default="pipeline-output.rar",
        help="Artifact path (.rar, .zip, or extracted directory).",
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
