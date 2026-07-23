# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for canonical manifest serialization and signature verification."""
import pytest
from configstream.signer import Signer, _canonical_manifest_payload

def test_canonical_manifest_payload_sorting():
    manifest_a = {"version": "3.1.0", "count": 100, "meta": {"b": 2, "a": 1}}
    manifest_b = {"meta": {"a": 1, "b": 2}, "count": 100, "version": "3.1.0"}

    timestamp = 1700000000
    payload_a = _canonical_manifest_payload(manifest_a, timestamp)
    payload_b = _canonical_manifest_payload(manifest_b, timestamp)

    # Key insertion order must produce identical canonical byte strings
    assert payload_a == payload_b
