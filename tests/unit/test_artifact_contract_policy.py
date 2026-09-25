# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

import pytest

from configstream.constants import ARTIFACT_TRANSIENT_SUFFIXES
from configstream.output_logic import write_public_artifact_contract
from scripts import (
    finalize_release_outputs,
    native_client_checks,
    refresh_shard_contract,
    release_gate,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _connectivity_check(**overrides: object) -> dict[str, object]:
    check: dict[str, object] = {
        "core": "sing-box-connectivity:trojan",
        "path": "proxies.json",
        "status": "failed",
        "error": "release sing-box connectivity failed for: trojan",
        "attempted": 5,
        "eligible_candidates": 5,
    }
    check.update(overrides)
    return check


def test_exhausted_connectivity_pool_does_not_fail_native_validation() -> None:
    """Run 36090088938 failed only because all 5 trojan endpoints were dead.

    Those proxies are third-party and ephemeral. The bounded second wave
    retried the whole eligible pool and still found nothing alive, which is an
    availability observation, so the stage must exit zero. Every other check
    still has to pass, and the failure is still recorded in the report.
    """
    check = _connectivity_check()

    assert native_client_checks._blocks_release(check) is False


def test_connectivity_failures_without_proven_exhaustion_still_fail() -> None:
    assert (
        native_client_checks._blocks_release(_connectivity_check(attempted=3)) is True
    )
    assert (
        native_client_checks._blocks_release(_connectivity_check(attempted=0)) is True
    )
    assert (
        native_client_checks._blocks_release(_connectivity_check(eligible_candidates=9))
        is True
    )


def test_missing_exhaustion_evidence_fails_closed() -> None:
    check = _connectivity_check()
    del check["attempted"]
    del check["eligible_candidates"]

    assert native_client_checks._blocks_release(check) is True


def test_unrelated_native_failures_are_never_excused() -> None:
    assert (
        native_client_checks._blocks_release(
            {
                "core": "sing-box",
                "path": "singbox.json",
                "status": "failed",
                "error": "config rejected",
            }
        )
        is True
    )
    # The bare connectivity core has no per-protocol evidence at all.
    assert (
        native_client_checks._blocks_release(
            {
                "core": "sing-box-connectivity",
                "path": "proxies.json",
                "status": "failed",
                "error": "version mismatch",
                "attempted": 3,
                "eligible_candidates": 3,
            }
        )
        is True
    )
    # A skipped connectivity check is unenforced evidence, not availability.
    assert (
        native_client_checks._blocks_release(_connectivity_check(status="skipped"))
        is True
    )


def test_release_gate_accepts_exhausted_connectivity_but_rejects_partial_sweep(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The release gate is the second enforcement point that failed in CI."""
    for path in {"proxies.json", *release_gate.REQUIRED_NATIVE_TARGETS.values()}:
        (tmp_path / path).write_text("[]", encoding="utf-8")
    monkeypatch.setattr(release_gate, "digest", lambda _path: "a" * 64)
    # The gate binds report provenance to the CI environment, so pin both sides
    # instead of depending on whether GITHUB_* happens to be set on the host.
    provenance = {
        "GITHUB_SHA": "test-source-commit",
        "GITHUB_RUN_ID": "test-run-id",
        "GITHUB_RUN_ATTEMPT": "1",
    }
    for name, value in provenance.items():
        monkeypatch.setenv(name, value)

    def _report(check: dict[str, object]) -> dict[str, object]:
        check = dict(check)
        check.setdefault("artifact_sha256", "a" * 64)
        check.setdefault("binary_sha256", "a" * 64)
        required = [
            {
                "core": core,
                "path": path,
                "status": "passed",
                "artifact_sha256": "a" * 64,
                "binary_sha256": "a" * 64,
                "error": None,
            }
            for core, path in release_gate.REQUIRED_NATIVE_TARGETS.items()
        ]
        checks = [*required, check]
        return {
            "schema_version": 2,
            "source_commit": provenance["GITHUB_SHA"],
            "run_id": provenance["GITHUB_RUN_ID"],
            "run_attempt": provenance["GITHUB_RUN_ATTEMPT"],
            "checks": checks,
            "summary": {
                "passed": len(required),
                "failed": 1,
                "skipped": 0,
            },
            "tools": {
                name: {
                    "available": True,
                    "binary": name,
                    "binary_sha256": "a" * 64,
                }
                for name in ("sing-box", "mihomo", "xray")
            },
        }

    def _errors(check: dict[str, object]) -> list[str]:
        return release_gate.validate_native_report(tmp_path, _report(check))

    assert _errors(_connectivity_check()) == []
    assert any(
        "connectivity:trojan" in error
        for error in _errors(_connectivity_check(attempted=3))
    )


def test_public_manifest_excludes_all_canonical_transients(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CS_SIGNING_PRIVATE_KEY_HEX", raising=False)
    (tmp_path / "metadata.json").write_text(
        json.dumps({"total_working": 1, "total_tested": 1}), encoding="utf-8"
    )
    (tmp_path / "stable.txt").write_text("stable", encoding="utf-8")
    for suffix in ARTIFACT_TRANSIENT_SUFFIXES:
        (tmp_path / f"ephemeral{suffix}").write_text("transient", encoding="utf-8")

    manifest = write_public_artifact_contract(tmp_path)
    paths = {str(item["path"]) for item in manifest["files"]}

    assert "stable.txt" in paths
    assert not any(path.endswith(ARTIFACT_TRANSIENT_SUFFIXES) for path in paths)


def test_public_manifest_excludes_unservable_pages_dotfiles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CS_SIGNING_PRIVATE_KEY_HEX", raising=False)
    (tmp_path / "metadata.json").write_text(
        json.dumps({"total_working": 1, "total_tested": 1}), encoding="utf-8"
    )
    (tmp_path / ".nojekyll").touch()
    (tmp_path / ".build-config.json").write_text("{}", encoding="utf-8")

    manifest = write_public_artifact_contract(tmp_path)
    paths = {str(item["path"]) for item in manifest["files"]}

    assert "metadata.json" in paths
    assert ".nojekyll" not in paths
    assert ".build-config.json" not in paths


def _remove_transients(root: Path) -> None:
    """Mirror the release finalizer, which clears transients before gating."""
    for path in root.rglob("*"):
        if path.is_file() and path.name.endswith(ARTIFACT_TRANSIENT_SUFFIXES):
            path.unlink()


def test_release_gate_manifest_ignores_unservable_pages_dotfiles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CS_SIGNING_PRIVATE_KEY_HEX", raising=False)
    (tmp_path / "metadata.json").write_text(
        json.dumps({"total_working": 1, "total_tested": 1}), encoding="utf-8"
    )
    (tmp_path / "stable.txt").write_text("stable", encoding="utf-8")
    (tmp_path / ".nojekyll").touch()
    (tmp_path / ".build-config.json").write_text("{}", encoding="utf-8")

    manifest = write_public_artifact_contract(tmp_path)
    listed = {str(item["path"]) for item in manifest["files"]}
    _remove_transients(tmp_path)

    assert ".nojekyll" not in listed
    assert ".build-config.json" not in listed
    assert release_gate.validate_manifest(tmp_path, manifest) == []


def test_release_gate_manifest_rejects_unservable_pages_dotfiles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CS_SIGNING_PRIVATE_KEY_HEX", raising=False)
    (tmp_path / "metadata.json").write_text(
        json.dumps({"total_working": 1, "total_tested": 1}), encoding="utf-8"
    )
    (tmp_path / ".nojekyll").touch()
    manifest = write_public_artifact_contract(tmp_path)
    manifest["files"].append({"path": ".nojekyll", "size_bytes": 0, "sha256": "0" * 64})
    _remove_transients(tmp_path)

    errors = release_gate.validate_manifest(tmp_path, manifest)

    assert "manifest path is not public payload: .nojekyll" in errors


def test_release_cleanup_uses_one_canonical_transient_policy() -> None:
    assert finalize_release_outputs.TRANSIENT_SUFFIXES is ARTIFACT_TRANSIENT_SUFFIXES
    assert refresh_shard_contract.TRANSIENT_SUFFIXES is ARTIFACT_TRANSIENT_SUFFIXES
    assert release_gate.TRANSIENT_SUFFIXES is ARTIFACT_TRANSIENT_SUFFIXES


def test_release_singbox_target_follows_runtime_manifest() -> None:
    runtime_manifest = REPO_ROOT / "config" / "runtime-versions.json"
    payload = json.loads(runtime_manifest.read_text(encoding="utf-8"))

    assert (
        finalize_release_outputs._release_singbox_version()
        == payload["sing_box"]["release_validator"]
    )
