# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

from configstream.signer import Signer
from scripts.release_gate import _sign_promoted_manifest
from scripts.validate_pages_signature_policy import validate_pages_signature_policy


def _write_manifest(root: Path, manifest: dict[str, object]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "artifact_manifest.json").write_text(
        json.dumps(manifest, sort_keys=True), encoding="utf-8"
    )


def _base_manifest() -> dict[str, object]:
    return {
        "schema_version": "2.0",
        "files": [],
        "file_count": 0,
        "total_size_bytes": 0,
    }


def test_unsigned_pages_are_rejected_by_default(tmp_path: Path) -> None:
    _write_manifest(tmp_path, _base_manifest())

    errors = validate_pages_signature_policy(tmp_path)

    assert any(
        "unsigned Pages publication is disabled by default" in error for error in errors
    )


def test_unsigned_pages_require_explicit_opt_in(tmp_path: Path) -> None:
    _write_manifest(tmp_path, _base_manifest())

    assert validate_pages_signature_policy(tmp_path, allow_unsigned=True) == []


def test_signed_pages_cannot_fall_back_to_unsigned_policy(tmp_path: Path) -> None:
    manifest = _base_manifest()
    _sign_promoted_manifest(manifest, "11" * 32)
    _write_manifest(tmp_path, manifest)

    errors = validate_pages_signature_policy(tmp_path, allow_unsigned=True)

    assert any(
        "signed artifacts must never be accepted without a trust anchor" in error
        for error in errors
    )


def test_signed_pages_verify_against_configured_trust_anchor(tmp_path: Path) -> None:
    private_key = "11" * 32
    signer = Signer(private_key)
    manifest = _base_manifest()
    _sign_promoted_manifest(manifest, private_key)
    _write_manifest(tmp_path, manifest)

    assert (
        validate_pages_signature_policy(
            tmp_path,
            public_key=signer.get_public_key_hex(),
        )
        == []
    )


def test_invalid_configured_public_key_is_not_treated_as_missing(
    tmp_path: Path,
) -> None:
    _write_manifest(tmp_path, _base_manifest())

    errors = validate_pages_signature_policy(
        tmp_path,
        public_key="not-a-valid-ed25519-key",
        allow_unsigned=True,
    )

    assert errors == ["configured Pages public key is not a valid Ed25519 public key"]


def test_invalid_signature_fails_closed_with_valid_trust_anchor(tmp_path: Path) -> None:
    private_key = "11" * 32
    signer = Signer(private_key)
    manifest = _base_manifest()
    _sign_promoted_manifest(manifest, private_key)
    signature = manifest["manifest_signature"]
    assert isinstance(signature, dict)
    signature["signature"] = "00" * 64
    _write_manifest(tmp_path, manifest)

    assert validate_pages_signature_policy(
        tmp_path,
        public_key=signer.get_public_key_hex(),
    ) == ["artifact_manifest.json manifest signature verification failed"]
