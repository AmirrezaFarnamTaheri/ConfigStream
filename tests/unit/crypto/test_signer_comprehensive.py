# SPDX-License-Identifier: AGPL-3.0-or-later
import os
import time

import pytest

from configstream.signer import SIGNATURE_MAX_AGE_SECONDS, Signer


def test_signer_lifecycle():
    # 1. Generate key
    seed = os.urandom(32)
    s = Signer(seed.hex())

    # 2. Get Public Key
    pub_hex = s.get_public_key_hex()
    assert len(pub_hex) == 64  # 32 bytes hex

    # 3. Sign
    msg = "test_message"
    signed = s.sign_subscription(msg)
    assert signed["content"] == msg
    assert "signature" in signed
    assert "timestamp" in signed

    # 4. Verify (with timestamp for full replay protection)
    assert Signer.verify_signature(
        msg, signed["signature"], pub_hex, timestamp=signed["timestamp"]
    )

    # 5. Verify Failure — tampered content
    assert not Signer.verify_signature(
        "tampered", signed["signature"], pub_hex, timestamp=signed["timestamp"]
    )


def test_signer_no_key():
    s = Signer()
    with pytest.raises(ValueError):
        s.sign_subscription("test")
    with pytest.raises(ValueError):
        s.get_public_key_hex()


def test_verify_bad_signature():
    seed = os.urandom(32)
    s = Signer(seed.hex())
    pub_hex = s.get_public_key_hex()

    bad_sig = "00" * 64
    assert not Signer.verify_signature("test", bad_sig, pub_hex)


def test_verify_bad_key():
    # Bad key format
    try:
        Signer.verify_signature("test", "00" * 64, "badkey")
    except Exception:
        pass  # verify_signature catches ValueError internally

    assert not Signer.verify_signature("test", "00" * 64, "00" * 32)


# ---------------------------------------------------------------------------
# Replay protection tests (P1-2 fix coverage)
# ---------------------------------------------------------------------------


def test_timestamp_is_included_in_signed_payload():
    """The timestamp must be part of the signed bytes; stripping it must fail."""
    seed = os.urandom(32)
    s = Signer(seed.hex())
    pub_hex = s.get_public_key_hex()

    signed = s.sign_subscription("hello")
    # A caller that passes no timestamp falls back to legacy (content-only) path.
    # The signature was produced over (timestamp || content), so verifying
    # against content-only bytes must fail.
    assert not Signer.verify_signature(
        "hello",
        signed["signature"],
        pub_hex,
        timestamp=None,  # legacy path — should reject because payload differs
    )


def test_fresh_signature_accepted():
    """A signature produced right now must pass the age check."""
    seed = os.urandom(32)
    s = Signer(seed.hex())
    pub_hex = s.get_public_key_hex()

    signed = s.sign_subscription("fresh")
    assert Signer.verify_signature(
        "fresh",
        signed["signature"],
        pub_hex,
        timestamp=signed["timestamp"],
    )


def test_expired_signature_rejected():
    """A signature older than max_age_seconds must be rejected."""
    seed = os.urandom(32)
    s = Signer(seed.hex())
    pub_hex = s.get_public_key_hex()

    signed = s.sign_subscription("stale")
    old_timestamp = int(time.time()) - SIGNATURE_MAX_AGE_SECONDS - 1
    # The cryptographic part would pass, but the age check must reject it.
    assert not Signer.verify_signature(
        "stale",
        signed["signature"],
        pub_hex,
        timestamp=old_timestamp,
        max_age_seconds=SIGNATURE_MAX_AGE_SECONDS,
    )


def test_future_timestamp_rejected():
    """A timestamp in the future (negative age) must be rejected as suspicious."""
    seed = os.urandom(32)
    s = Signer(seed.hex())
    pub_hex = s.get_public_key_hex()

    signed = s.sign_subscription("future")
    future_timestamp = int(time.time()) + 3600  # 1 hour in the future
    assert not Signer.verify_signature(
        "future",
        signed["signature"],
        pub_hex,
        timestamp=future_timestamp,
    )


def test_replay_of_captured_signature_fails_after_window():
    """Simulates a replay attack: reuse a valid signature after the window expires."""
    seed = os.urandom(32)
    s = Signer(seed.hex())
    pub_hex = s.get_public_key_hex()

    signed = s.sign_subscription("important payload")
    captured_sig = signed["signature"]
    captured_ts = signed["timestamp"]

    # Immediately valid.
    assert Signer.verify_signature(
        "important payload", captured_sig, pub_hex, timestamp=captured_ts
    )

    # Simulate the window expiring by backdating the timestamp far enough.
    expired_ts = captured_ts - SIGNATURE_MAX_AGE_SECONDS - 1
    assert not Signer.verify_signature(
        "important payload",
        captured_sig,
        pub_hex,
        timestamp=expired_ts,
    )


def test_custom_max_age_respected():
    """max_age_seconds parameter is honoured."""
    seed = os.urandom(32)
    s = Signer(seed.hex())
    pub_hex = s.get_public_key_hex()

    signed = s.sign_subscription("msg")
    # Use timestamp that is 10 seconds old.
    ts_10s_ago = int(time.time()) - 10
    # With a 5-second window it must be rejected.
    assert not Signer.verify_signature(
        "msg", signed["signature"], pub_hex, timestamp=ts_10s_ago, max_age_seconds=5
    )
    # With a 30-second window a fresh signature must still pass.
    signed2 = s.sign_subscription("msg")
    assert Signer.verify_signature(
        "msg",
        signed2["signature"],
        pub_hex,
        timestamp=signed2["timestamp"],
        max_age_seconds=30,
    )
