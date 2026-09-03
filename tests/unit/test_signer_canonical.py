import json
import time
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from configstream.signer import (
    Signer,
    _canonical_manifest_payload,
    _build_signed_payload,
    normalize_public_key_hex,
)


def test_canonical_manifest_payload_and_negative_vectors() -> None:
    # 1. Test canonical serialization format
    manifest = {
        "version": "3.2.0",
        "generated_at": 1725321600,
        "files": ["proxies.json", "metadata.json"],
        "nested": {"z": 1, "a": 2},
    }
    ts = 1725321600
    payload_bytes = _canonical_manifest_payload(manifest, ts)

    # 8-byte big endian timestamp prefix + canonical JSON
    assert len(payload_bytes) > 8
    json_part = payload_bytes[8:].decode("utf-8")
    assert (
        json_part
        == '{"files":["proxies.json","metadata.json"],"generated_at":1725321600,"nested":{"a":2,"z":1},"version":"3.2.0"}'
    )

    # 2. Key generation & signature verification
    priv_key = ed25519.Ed25519PrivateKey.generate()
    priv_hex = priv_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    ).hex()
    pub_hex = (
        priv_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        .hex()
    )

    signer = Signer(private_key_hex=priv_hex)
    signed_data = signer.sign_subscription("test-subscription-content")

    # Verify valid signature
    assert (
        signer.verify_subscription(
            signed_data["content"],
            signed_data["signature"],
            pub_hex,
            timestamp=signed_data["timestamp"],
        )
        is True
    )

    # Negative test 1: Tampered content
    assert (
        signer.verify_subscription(
            "tampered-content",
            signed_data["signature"],
            pub_hex,
            timestamp=signed_data["timestamp"],
        )
        is False
    )

    # Negative test 2: Tampered timestamp
    assert (
        signer.verify_subscription(
            signed_data["content"],
            signed_data["signature"],
            pub_hex,
            timestamp=signed_data["timestamp"] + 10,
        )
        is False
    )
    # Negative test 3: Mismatched public key
    other_priv = ed25519.Ed25519PrivateKey.generate()
    other_pub_hex = (
        other_priv.public_key()
        .public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        .hex()
    )
    assert (
        signer.verify_subscription(
            signed_data["content"],
            signed_data["signature"],
            other_pub_hex,
            timestamp=signed_data["timestamp"],
        )
        is False
    )
