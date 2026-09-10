# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bounded release-runtime connectivity conformance for sing-box.

The fast embedded Go tester intentionally remains a pre-release screening path.
Before publication, this module rechecks deterministic representatives from the
sealed ``proxies.json`` with the separately installed release-authority sing-box
binary.  This closes semantic drift between the embedded tester and the client
version whose configuration is actually published without turning release
validation into an unbounded full retest.
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess  # nosec B404
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

from ..config import AppSettings
from ..models import Proxy
from ..security_validator import SecurityValidator
from .python import PythonTester

SAMPLES_PER_PROTOCOL = 3
MAX_CONCURRENCY = 4
PROBE_TIMEOUT_SECONDS = 12.0
_VERSION_RE = re.compile(r"\bversion\s+v?(\d+\.\d+\.\d+)\b", re.IGNORECASE)
_EXCLUDED_PROTOCOLS = {"openvpn", "unknown", "revived"}


def expected_singbox_version(repo_root: Path) -> str:
    payload = json.loads(
        (repo_root / "config/runtime-versions.json").read_text(encoding="utf-8")
    )
    value = payload.get("sing_box", {}).get("release_validator")
    if not isinstance(value, str) or not re.fullmatch(r"\d+\.\d+\.\d+", value):
        raise ValueError("runtime-versions.json has no valid sing_box.release_validator")
    return value


def observed_singbox_version(binary: Path) -> str | None:
    try:
        completed = subprocess.run(  # nosec B603
            [str(binary), "version"],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    output = f"{completed.stdout}\n{completed.stderr}"
    match = _VERSION_RE.search(output)
    return match.group(1) if match else None


def select_samples(records: Iterable[object]) -> dict[str, list[Proxy]]:
    """Select the lowest-latency deterministic representatives per protocol."""
    grouped: dict[str, list[Proxy]] = defaultdict(list)
    for raw in records:
        if not isinstance(raw, dict):
            continue
        try:
            proxy = Proxy.model_validate(raw)
        except ValidationError:
            continue
        protocol = proxy.protocol.lower()
        if protocol in _EXCLUDED_PROTOCOLS or not proxy.config or not proxy.is_working:
            continue
        grouped[protocol].append(proxy)

    selected: dict[str, list[Proxy]] = {}
    for protocol, proxies in grouped.items():
        proxies.sort(
            key=lambda item: (
                item.latency is None,
                float(item.latency) if item.latency is not None else float("inf"),
                item.id,
            )
        )
        selected[protocol] = proxies[:SAMPLES_PER_PROTOCOL]
    return dict(sorted(selected.items()))


async def _probe(
    tester: PythonTester,
    protocol: str,
    proxy: Proxy,
    semaphore: asyncio.Semaphore,
) -> tuple[str, bool, str | None]:
    async with semaphore:
        candidate = proxy.model_copy(deep=True)
        candidate.is_working = False
        candidate.latency = None
        try:
            result = await asyncio.wait_for(
                tester.test_via_singbox(candidate),
                timeout=PROBE_TIMEOUT_SECONDS + 5.0,
            )
        except asyncio.TimeoutError:
            return protocol, False, "native connectivity probe timed out"
        if result.is_working:
            return protocol, True, None
        category = str(
            (result.details or {}).get("tester_error_category") or "probe_failed"
        )
        return protocol, False, SecurityValidator.sanitize_log_message(category)


async def run_release_runtime_conformance(
    release_root: Path,
    *,
    singbox_binary: Path,
    repo_root: Path,
) -> dict[str, Any]:
    """Retest bounded protocol representatives with the release sing-box binary."""
    expected = expected_singbox_version(repo_root)
    observed = observed_singbox_version(singbox_binary)
    base: dict[str, Any] = {
        "expected_version": expected,
        "observed_version": observed,
        "sample_limit_per_protocol": SAMPLES_PER_PROTOCOL,
        "protocols": {},
        "status": "failed",
    }
    if observed != expected:
        base["error"] = "installed sing-box version does not match release authority"
        return base

    proxies_path = release_root / "proxies.json"
    try:
        records = json.loads(proxies_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        base["error"] = "proxies.json is unavailable or invalid"
        return base
    if not isinstance(records, list):
        base["error"] = "proxies.json must be a list"
        return base

    samples = select_samples(records)
    if not samples:
        base["error"] = "no working release proxies are eligible for native conformance"
        return base

    tester = PythonTester(
        AppSettings(), timeout=PROBE_TIMEOUT_SECONDS, strict_security=False
    )
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    tasks = [
        _probe(tester, protocol, proxy, semaphore)
        for protocol, proxies in samples.items()
        for proxy in proxies
    ]
    results = await asyncio.gather(*tasks)

    by_protocol: dict[str, list[tuple[bool, str | None]]] = defaultdict(list)
    for protocol, passed, error in results:
        by_protocol[protocol].append((passed, error))

    failed_protocols: list[str] = []
    rendered: dict[str, Any] = {}
    for protocol in sorted(samples):
        outcomes = by_protocol.get(protocol, [])
        passed = sum(ok for ok, _ in outcomes)
        attempted = len(outcomes)
        status = "passed" if passed > 0 else "failed"
        if status != "passed":
            failed_protocols.append(protocol)
        errors = sorted({error for ok, error in outcomes if not ok and error})
        rendered[protocol] = {
            "status": status,
            "attempted": attempted,
            "passed": passed,
            "errors": errors[:3],
        }

    base["protocols"] = rendered
    base["status"] = "passed" if not failed_protocols else "failed"
    if failed_protocols:
        base["error"] = "release sing-box connectivity failed for: " + ", ".join(
            failed_protocols
        )
    return base


def conformance_checks(
    conformance: dict[str, Any],
    *,
    proxies_digest: str,
    binary_digest: str,
) -> list[dict[str, Any]]:
    """Render conformance into native-report checks enforced by release_gate.py."""
    protocols = conformance.get("protocols")
    if not isinstance(protocols, dict) or not protocols:
        return [
            {
                "core": "sing-box-connectivity",
                "path": "proxies.json",
                "status": "failed",
                "command": ["sing-box", "release-runtime-connectivity"],
                "artifact_sha256": proxies_digest,
                "binary_sha256": binary_digest,
                "error": str(
                    conformance.get("error") or "native conformance unavailable"
                ),
            }
        ]

    checks: list[dict[str, Any]] = []
    for protocol, result in sorted(protocols.items()):
        if not isinstance(result, dict):
            continue
        checks.append(
            {
                "core": f"sing-box-connectivity:{protocol}",
                "path": "proxies.json",
                "status": "passed"
                if result.get("status") == "passed"
                else "failed",
                "command": ["sing-box", "release-runtime-connectivity", protocol],
                "artifact_sha256": proxies_digest,
                "binary_sha256": binary_digest,
                "error": None
                if result.get("status") == "passed"
                else str(conformance.get("error") or "native connectivity failed"),
            }
        )
    return checks
