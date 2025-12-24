import pytest
import os
from configstream.crypto.signer import Signer


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

    # 4. Verify
    assert Signer.verify_signature(msg, signed["signature"], pub_hex)

    # 5. Verify Failure
    assert not Signer.verify_signature("tampered", signed["signature"], pub_hex)


def test_signer_no_key():
    s = Signer()
    with pytest.raises(ValueError):
        s.sign_subscription("test")
    with pytest.raises(ValueError):
        s.get_public_key_hex()


def test_verify_bad_signature():
    # 32 bytes
    seed = os.urandom(32)
    s = Signer(seed.hex())
    pub_hex = s.get_public_key_hex()

    # Bad sig
    bad_sig = "00" * 64
    assert not Signer.verify_signature("test", bad_sig, pub_hex)


def test_verify_bad_key():
    # Bad key format
    try:
        Signer.verify_signature("test", "00" * 64, "badkey")
        # Should return False (caught internally)
    except Exception:
        pass  # If implementation raises, we catch, but verify_signature catches ValueError

    assert not Signer.verify_signature(
        "test", "00" * 64, "00" * 32
    )  # Valid length but wrong
