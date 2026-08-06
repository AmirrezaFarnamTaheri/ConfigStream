# SPDX-License-Identifier: AGPL-3.0-or-later
"""Snapshot a currently deployed Pages artifact after trust verification."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import socket
import json
import os
import re
import shutil
import tempfile
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import httpx

from configstream.signer import (
    CLOCK_SKEW_TOLERANCE_SECONDS,
    Signer,
    normalize_public_key_hex,
)

MAX_FILES = 10_000
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 1024 * 1024 * 1024
MIN_ROLLBACK_MAX_AGE_HOURS = 12
MAX_ROLLBACK_MAX_AGE_HOURS = 48
_SOURCE_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def _origin(parsed: urllib.parse.ParseResult) -> tuple[str, str, int]:
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").rstrip(".").lower()
    port = parsed.port or (443 if scheme == "https" else 80)
    return scheme, host, port


def _authority(host: str, port: int, scheme: str) -> str:
    parsed = ipaddress.ip_address(host) if _is_ip_literal(host) else None
    rendered = f"[{host}]" if isinstance(parsed, ipaddress.IPv6Address) else host
    default = 443 if scheme == "https" else 80
    return rendered if port == default else f"{rendered}:{port}"


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def _resolve_and_pin(
    parsed: urllib.parse.ParseResult,
    pins: dict[str, set[str]],
) -> set[str]:
    host = (parsed.hostname or "").rstrip(".").lower()
    if not host:
        raise ValueError("snapshot URL has no host")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if _is_ip_literal(host):
        resolved = {str(ipaddress.ip_address(host))}
    else:
        try:
            infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except (socket.gaierror, OSError) as exc:
            raise ValueError(f"snapshot DNS resolution failed for {host}") from exc
        resolved = {str(ipaddress.ip_address(info[4][0])) for info in infos}
    if not resolved:
        raise ValueError(f"snapshot DNS resolution returned no addresses for {host}")

    if _is_local_host(host):
        non_loopback = sorted(
            address
            for address in resolved
            if not ipaddress.ip_address(address).is_loopback
        )
        if non_loopback:
            raise ValueError(
                f"local snapshot host resolved outside loopback: {non_loopback[0]}"
            )
    else:
        non_global = sorted(
            address
            for address in resolved
            if not ipaddress.ip_address(address).is_global
        )
        if non_global:
            raise ValueError(f"snapshot host resolved to non-global address: {non_global[0]}")

    previous = pins.get(host)
    if previous is None:
        pins[host] = set(resolved)
        return set(resolved)
    allowed = previous & resolved
    if not allowed:
        raise ValueError(f"snapshot DNS rebinding detected for {host}")
    return allowed


def _fetch(
    url: str,
    timeout: float,
    pins: dict[str, set[str]] | None = None,
) -> bytes:
    pin_state = pins if pins is not None else {}
    source = urllib.parse.urlparse(url)
    source_origin = _origin(source)
    current_url = url

    with httpx.Client(follow_redirects=False, trust_env=False, timeout=timeout) as client:
        for _redirect in range(6):
            parsed = urllib.parse.urlparse(current_url)
            if _origin(parsed) != source_origin:
                raise ValueError("snapshot redirect crossed the trusted origin")
            if source_origin[0] == "https" and parsed.scheme.lower() != "https":
                raise ValueError("snapshot redirect attempted an HTTPS downgrade")
            if parsed.username or parsed.password:
                raise ValueError("snapshot URL must not contain credentials")

            allowed_ips = _resolve_and_pin(parsed, pin_state)
            target_ip = sorted(allowed_ips)[0]
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            logical_host = (parsed.hostname or "").rstrip(".").lower()
            target_netloc = _authority(target_ip, port, parsed.scheme)
            target_url = urllib.parse.urlunparse(parsed._replace(netloc=target_netloc))
            headers = {
                "Accept": "*/*",
                "User-Agent": "ConfigStream rollback snapshot",
                "Host": _authority(logical_host, port, parsed.scheme),
            }
            request = client.build_request("GET", target_url, headers=headers)
            if parsed.scheme == "https":
                request.extensions["sni_hostname"] = logical_host

            response = client.send(request, stream=True)
            try:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("snapshot redirect omitted Location")
                    current_url = urllib.parse.urljoin(current_url, location)
                    continue
                if response.status_code < 200 or response.status_code >= 300:
                    raise ValueError(
                        f"snapshot source returned HTTP {response.status_code}: {current_url}"
                    )
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_FILE_BYTES:
                        raise ValueError(f"snapshot file exceeds size limit: {current_url}")
                return bytes(body)
            finally:
                response.close()
    raise ValueError("snapshot exceeded redirect limit")


def _safe_relative(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or "\x00" in value
        or "?" in value
        or "#" in value
    ):
        raise ValueError(f"unsafe manifest path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe manifest path: {value!r}")
    return path.as_posix()


def _join(base_url: str, relative: str) -> str:
    base = base_url if base_url.endswith("/") else base_url + "/"
    return urllib.parse.urljoin(base, relative)


def _is_local_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    normalized = hostname.rstrip(".").lower()
    if normalized == "localhost" or normalized.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _parse_base_url(base_url: str) -> tuple[urllib.parse.ParseResult, bool]:
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base_url must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password:
        raise ValueError("base_url must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("base_url must not contain a query or fragment")
    is_local = _is_local_host(parsed.hostname)
    if not is_local and parsed.scheme != "https":
        raise ValueError("public rollback snapshots require HTTPS")
    return parsed, is_local


def _json_object(body: bytes, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return payload


def _parse_timestamp(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is missing a timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} has an invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def _rollback_max_age_seconds(metadata: dict[str, Any]) -> int:
    interval = metadata.get("update_interval_hours", 4)
    if isinstance(interval, bool) or not isinstance(interval, (int, float)) or interval <= 0:
        raise ValueError("metadata update_interval_hours must be positive")
    max_age_hours = max(MIN_ROLLBACK_MAX_AGE_HOURS, float(interval) * 2)
    max_age_hours = min(MAX_ROLLBACK_MAX_AGE_HOURS, max_age_hours)
    return int(max_age_hours * 60 * 60)


def _validate_body(relative: str, body: bytes, expected_size: int, expected_digest: str) -> None:
    if len(body) != expected_size:
        raise ValueError(f"size mismatch for {relative}")
    actual_digest = hashlib.sha256(body).hexdigest()
    if actual_digest != expected_digest:
        raise ValueError(f"hash mismatch for {relative}")


def _validate_release_eligibility(
    manifest: dict[str, Any],
    metadata: dict[str, Any],
    health: dict[str, Any],
    *,
    is_local: bool,
    public_key_value: str,
) -> tuple[bool, int, str]:
    max_age_seconds = _rollback_max_age_seconds(metadata)
    public_key_hex = normalize_public_key_hex(public_key_value)
    signature_required = not is_local
    signature_present = isinstance(manifest.get("manifest_signature"), dict)

    if signature_required and not public_key_hex:
        raise ValueError("public rollback snapshot requires a configured CS_PUBLIC_KEY")
    if signature_required and not signature_present:
        raise ValueError("public rollback snapshot requires a signed artifact manifest")

    signature_verified = False
    if signature_present or public_key_hex:
        if not public_key_hex:
            raise ValueError("signed artifact manifest cannot be verified without CS_PUBLIC_KEY")
        signature_verified = Signer.verify_manifest_signature(
            manifest,
            public_key_hex,
            max_age_seconds=max_age_seconds,
        )
        if not signature_verified:
            raise ValueError("artifact manifest signature is invalid or stale")

    source_commit = manifest.get("source_commit")
    if not is_local and (
        not isinstance(source_commit, str) or not _SOURCE_COMMIT_RE.fullmatch(source_commit)
    ):
        raise ValueError("public rollback snapshot requires a 40-character source commit")

    health_status = health.get("status")
    if health_status != "ok":
        raise ValueError(f"rollback source health is {health_status or 'unknown'}")
    working = health.get("total_working", metadata.get("total_working", 0))
    if isinstance(working, bool) or not isinstance(working, (int, float)) or working <= 0:
        raise ValueError("rollback source contains no verified working proxies")
    if health.get("schema_validated") is not True:
        raise ValueError("rollback source was not schema validated")

    generated_value = metadata.get("last_updated_utc") or metadata.get("generated_at")
    generated_at = _parse_timestamp(generated_value, "metadata")
    now = datetime.now(timezone.utc)
    age_seconds = (now - generated_at).total_seconds()
    if age_seconds < -CLOCK_SKEW_TOLERANCE_SECONDS:
        raise ValueError("rollback source metadata timestamp is in the future")
    if age_seconds > max_age_seconds:
        raise ValueError("rollback source metadata is stale")

    health_commit = health.get("source_commit")
    metadata_commit = metadata.get("source_commit")
    for label, candidate in (("health", health_commit), ("metadata", metadata_commit)):
        if candidate and source_commit and candidate != source_commit:
            raise ValueError(f"{label} source commit does not match the manifest")

    return signature_verified, max_age_seconds, generated_at.isoformat()



def _recover_interrupted_swap(destination: Path) -> None:
    """Restore a last-known-good snapshot left by an interrupted directory swap."""

    backup = destination.with_name(destination.name + ".replaced")
    if backup.exists() and not destination.exists():
        os.replace(backup, destination)
    elif backup.exists():
        shutil.rmtree(backup)


def snapshot(
    base_url: str,
    destination: Path,
    *,
    timeout: float = 20.0,
    public_key: str | None = None,
) -> dict[str, Any]:
    _, is_local = _parse_base_url(base_url)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    _recover_interrupted_swap(destination)
    pins: dict[str, set[str]] = {}
    manifest_body = _fetch(_join(base_url, "artifact_manifest.json"), timeout, pins)
    manifest = _json_object(manifest_body, "artifact manifest")
    if not isinstance(manifest.get("files"), list):
        raise ValueError("artifact manifest must contain a files list")
    raw_files = manifest["files"]
    if not raw_files or len(raw_files) > MAX_FILES:
        raise ValueError("artifact manifest file count is outside allowed bounds")

    planned: list[tuple[str, int, str]] = []
    entries: dict[str, tuple[int, str]] = {}
    total_expected = 0
    for item in raw_files:
        if not isinstance(item, dict):
            raise ValueError("artifact manifest contains a non-object entry")
        relative = _safe_relative(item.get("path"))
        if relative == "artifact_manifest.json":
            raise ValueError("artifact manifest must not list itself")
        if relative in entries:
            raise ValueError(f"duplicate manifest path: {relative}")
        size = item.get("size_bytes")
        digest = item.get("sha256")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0 or size > MAX_FILE_BYTES:
            raise ValueError(f"invalid manifest size for {relative}")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"invalid manifest hash for {relative}")
        total_expected += size
        if total_expected > MAX_TOTAL_BYTES:
            raise ValueError("snapshot exceeds aggregate size limit")
        entries[relative] = (size, digest)
        planned.append((relative, size, digest))

    missing_controls = {"metadata.json", "health.json"} - entries.keys()
    if missing_controls:
        raise ValueError(
            "artifact manifest is missing rollback control files: "
            + ", ".join(sorted(missing_controls))
        )

    prefetched: dict[str, bytes] = {}
    for relative in ("metadata.json", "health.json"):
        body = _fetch(_join(base_url, relative), timeout, pins)
        expected_size, expected_digest = entries[relative]
        _validate_body(relative, body, expected_size, expected_digest)
        prefetched[relative] = body

    metadata = _json_object(prefetched["metadata.json"], "metadata.json")
    health = _json_object(prefetched["health.json"], "health.json")
    signature_verified, max_age_seconds, generated_at = _validate_release_eligibility(
        manifest,
        metadata,
        health,
        is_local=is_local,
        public_key_value=public_key if public_key is not None else os.environ.get("CS_PUBLIC_KEY", ""),
    )

    with tempfile.TemporaryDirectory(prefix=f".{destination.name}-", dir=destination.parent) as temporary:
        stage = Path(temporary) / destination.name
        stage.mkdir()
        for relative, expected_size, expected_digest in planned:
            body = prefetched.get(relative)
            if body is None:
                body = _fetch(_join(base_url, relative), timeout, pins)
                _validate_body(relative, body, expected_size, expected_digest)
            target = stage.joinpath(*PurePosixPath(relative).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        (stage / "artifact_manifest.json").write_bytes(manifest_body)
        report = {
            "schema_version": 2,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "source_url": base_url,
            "source_commit": str(manifest.get("source_commit") or ""),
            "release_id": str(manifest.get("release_id") or ""),
            "file_count": len(planned),
            "total_size_bytes": total_expected,
            "manifest_sha256": hashlib.sha256(manifest_body).hexdigest(),
            "manifest_signature_verified": signature_verified,
            "health_status": health.get("status"),
            "total_working": int(health.get("total_working", 0)),
            "artifact_generated_at": generated_at,
            "max_age_seconds": max_age_seconds,
            "local_source": is_local,
        }
        backup = destination.with_name(destination.name + ".replaced")
        if backup.exists():
            shutil.rmtree(backup)
        if destination.exists():
            os.replace(destination, backup)
        try:
            os.replace(stage, destination)
        except OSError:
            if backup.exists() and not destination.exists():
                os.replace(backup, destination)
            raise
        else:
            if backup.exists():
                shutil.rmtree(backup)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url")
    parser.add_argument("destination", type=Path)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--report-file", type=Path)
    parser.add_argument(
        "--public-key",
        default=None,
        help="Ed25519 public key (Base64 SPKI or raw hex); defaults to CS_PUBLIC_KEY.",
    )
    args = parser.parse_args()
    try:
        report = snapshot(
            args.base_url,
            args.destination,
            timeout=args.timeout,
            public_key=args.public_key,
        )
    except (OSError, ValueError, httpx.HTTPError) as exc:
        print(f"ERROR: rollback snapshot failed: {type(exc).__name__}: {exc}")
        return 1
    if args.report_file:
        args.report_file.parent.mkdir(parents=True, exist_ok=True)
        args.report_file.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
