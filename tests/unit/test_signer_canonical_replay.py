# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for canonical manifest serialization and signature verification."""

import base64
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import configstream.signer as signer_module
from configstream.signer import (
    Signer,
    _canonical_manifest_payload,
    normalize_public_key_hex,
)
from scripts.validate_pages_artifact import _validate_manifest_signature


def test_canonical_manifest_payload_sorting() -> None:
    manifest_a = {"version": "3.1.0", "count": 100, "meta": {"b": 2, "a": 1}}
    manifest_b = {"meta": {"a": 1, "b": 2}, "count": 100, "version": "3.1.0"}

    timestamp = 1700000000
    payload_a = _canonical_manifest_payload(manifest_a, timestamp)
    payload_b = _canonical_manifest_payload(manifest_b, timestamp)

    # Key insertion order must produce identical canonical byte strings
    assert payload_a == payload_b


def test_manifest_signature_roundtrip_verification() -> None:
    """Test full Ed25519 manifest signing and verification round-trip."""
    priv_key = ed25519.Ed25519PrivateKey.generate()
    seed_bytes = priv_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_key_hex = (
        priv_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        .hex()
    )

    signer = Signer(seed_bytes.hex())
    manifest = {
        "schema_version": "1.0",
        "generated_at": "2026-07-24T00:00:00Z",
        "file_count": 5,
        "total_size_bytes": 1024,
    }

    sig_info = signer.sign_manifest(manifest)
    manifest["manifest_signature"] = sig_info

    # Verification must succeed via Signer helper
    assert Signer.verify_manifest_signature(manifest, pub_key_hex) is True


def test_manifest_signature_remains_valid_after_short_token_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Static release manifests rely on signed metadata freshness, not a 5-minute TTL."""
    clock = [1_700_000_000]
    monkeypatch.setattr(signer_module.time, "time", lambda: clock[0])
    signer = Signer("22" * 32)
    public_key = signer.get_public_key_hex()
    manifest: dict[str, object] = {"schema_version": "1.0", "files": []}
    manifest["manifest_signature"] = signer.sign_manifest(manifest)

    clock[0] += 600
    assert Signer.verify_manifest_signature(manifest, public_key) is True
    assert (
        Signer.verify_manifest_signature(manifest, public_key, max_age_seconds=300)
        is False
    )


def test_public_key_normalization_accepts_browser_spki_and_raw_hex() -> None:
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    spki = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    assert normalize_public_key_hex(raw.hex()) == raw.hex()
    assert normalize_public_key_hex(base64.b64encode(spki).decode()) == raw.hex()
    assert normalize_public_key_hex("PLACEHOLDER_PUBLIC_KEY") == ""


def test_manifest_signature_validation_script_integration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test script _validate_manifest_signature with real signed payload."""
    priv_key = ed25519.Ed25519PrivateKey.generate()
    seed_bytes = priv_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_key_hex = (
        priv_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        .hex()
    )

    monkeypatch.setenv("CS_PUBLIC_KEY", pub_key_hex)

    signer = Signer(seed_bytes.hex())
    manifest = {
        "schema_version": "1.0",
        "generated_at": "2026-07-24T00:00:00Z",
        "file_count": 5,
        "total_size_bytes": 1024,
    }
    manifest["manifest_signature"] = signer.sign_manifest(manifest)

    errors = _validate_manifest_signature(manifest)
    assert errors == []
