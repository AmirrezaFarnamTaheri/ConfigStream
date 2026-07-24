# SPDX-License-Identifier: AGPL-3.0-or-later
"""KAT verification for Steganography LSB offset derivation."""

import pytest
from configstream.stego import derive_lsb_offsets


def test_hmac_lsb_offset_derivation_kat() -> None:
    """Verify deterministic HMAC-SHA256 LSB offset derivation against Known-Answer-Test."""
    secret_key = b"0123456789abcdef0123456789abcdef"
    max_index = 1000
    count = 16

    offsets = derive_lsb_offsets(secret_key, max_index, count)

    assert len(offsets) == count
    assert all(0 <= idx < max_index for idx in offsets)
    expected_golden = [
        479,
        422,
        917,
        374,
        699,
        588,
        11,
        727,
        87,
        794,
        259,
        186,
        908,
        819,
        462,
        545,
    ]
    assert offsets == expected_golden
