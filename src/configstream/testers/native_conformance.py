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
MAX_CANDIDATES_PER_PROTOCOL = 6
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
        raise ValueError(
            "runtime-versions.json has no valid sing_box.release_validator"
        )
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


def select_samples(
    records: Iterable[object], limit: int = SAMPLES_PER_PROTOCOL
) -> dict[str, list[Proxy]]:
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
        selected[protocol] = proxies[: max(1, limit)]
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
        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            return (
                protocol,
                False,
                SecurityValidator.sanitize_log_message(
                    f"native connectivity probe errored: {type(exc).__name__}"
                ),
            )
        if result.is_working:
            return protocol, True, None
        category = str(
            (result.details or {}).get("tester_error_category") or "probe_failed"
        )
        return protocol, False, SecurityValidator.sanitize_log_message(category)


async def _probe_samples(
    tester: PythonTester,
    samples: dict[str, list[Proxy]],
    semaphore: asyncio.Semaphore,
) -> list[tuple[str, bool, str | None]]:
    tasks = [
        _probe(tester, protocol, proxy, semaphore)
        for protocol, proxies in samples.items()
        for proxy in proxies
    ]
    return list(await asyncio.gather(*tasks))


def eligible_pool_sizes(records: Iterable[object]) -> dict[str, int]:
    """Count every eligible working candidate per protocol, ignoring sampling."""
    grouped: dict[str, int] = defaultdict(int)
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
        grouped[protocol] += 1
    return dict(sorted(grouped.items()))


async def run_release_runtime_conformance(
    release_root: Path,
    *,
    singbox_binary: Path,
    repo_root: Path,
) -> dict[str, Any]:
    """Retest bounded protocol representatives with the release sing-box binary."""
    expected = await asyncio.to_thread(expected_singbox_version, repo_root)
    observed = await asyncio.to_thread(observed_singbox_version, singbox_binary)
    base: dict[str, Any] = {
        "expected_version": expected,
        "observed_version": observed,
        "sample_limit_per_protocol": MAX_CANDIDATES_PER_PROTOCOL,
        "initial_sample_limit_per_protocol": SAMPLES_PER_PROTOCOL,
        "protocols": {},
        "status": "failed",
    }
    if observed != expected:
        base["error"] = "installed sing-box version does not match release authority"
        return base

    proxies_path = release_root / "proxies.json"
    try:
        proxies_text = await asyncio.to_thread(proxies_path.read_text, encoding="utf-8")
        records = json.loads(proxies_text)
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
    pool_sizes = eligible_pool_sizes(records)

    tester = PythonTester(
        AppSettings(), timeout=PROBE_TIMEOUT_SECONDS, strict_security=False
    )
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    results = await _probe_samples(tester, samples, semaphore)

    # A protocol only fails once every eligible release proxy has been retested.
    # Proxies are screened by the embedded tester minutes earlier, so a bounded
    # second wave over the remaining candidates absorbs that churn instead of
    # failing the whole release on the first wave being entirely dead.
    unresolved = {
        protocol
        for protocol in samples
        if not any(passed for probed, passed, _ in results if probed == protocol)
    }
    if unresolved:
        wider = select_samples(records, MAX_CANDIDATES_PER_PROTOCOL)
        retries: dict[str, list[Proxy]] = {}
        for protocol in sorted(unresolved):
            already = {proxy.id for proxy in samples.get(protocol, [])}
            remaining = [
                proxy for proxy in wider.get(protocol, []) if proxy.id not in already
            ]
            if remaining:
                retries[protocol] = remaining
        if retries:
            results.extend(await _probe_samples(tester, retries, semaphore))

    by_protocol: dict[str, list[tuple[bool, str | None]]] = defaultdict(list)
    for protocol, probe_passed, error in results:
        by_protocol[protocol].append((probe_passed, error))

    failed_protocols: list[str] = []
    rendered: dict[str, Any] = {}
    for protocol in sorted(samples):
        outcomes = by_protocol.get(protocol, [])
        passed_count = sum(ok for ok, _ in outcomes)
        attempted = len(outcomes)
        status = "passed" if passed_count > 0 else "failed"
        if status != "passed":
            failed_protocols.append(protocol)
        errors = sorted({error for ok, error in outcomes if not ok and error})
        rendered[protocol] = {
            "status": status,
            "attempted": attempted,
            "passed": passed_count,
            "eligible_candidates": pool_sizes.get(protocol, attempted),
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
        attempted = result.get("attempted")
        eligible = result.get("eligible_candidates")
        check: dict[str, Any] = {
            "core": f"sing-box-connectivity:{protocol}",
            "path": "proxies.json",
            "status": "passed" if result.get("status") == "passed" else "failed",
            "command": ["sing-box", "release-runtime-connectivity", protocol],
            "artifact_sha256": proxies_digest,
            "binary_sha256": binary_digest,
            "error": (
                None
                if result.get("status") == "passed"
                else str(conformance.get("error") or "native connectivity failed")
            ),
        }
        # Carry the bounded-sweep counters so the release gate can tell proven
        # upstream unavailability (an exhausted pool) from a real coverage gap.
        if not isinstance(attempted, bool) and isinstance(attempted, int):
            check["attempted"] = attempted
        if not isinstance(eligible, bool) and isinstance(eligible, int):
            check["eligible_candidates"] = eligible
        checks.append(check)
    return checks
