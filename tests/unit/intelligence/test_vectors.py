# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for vector generation."""

import json
from unittest.mock import patch
from configstream.intelligence.vectors import _compute_vector, generate_vectors
from configstream.models import Proxy


def test_compute_vector():
    p = Proxy(
        protocol="ss",
        address="1.1.1.1",
        port=80,
        country_code="US",
        latency=100.0,
        org="Google",
        config="conf",
    )

    vec = _compute_vector(p)
    assert len(vec) == 8
    # Protocol hash for 'ss' should be consistent
    # Latency 100 < 150 -> bucket 0
    assert vec[2] == 0
    # Port 80 % 10 -> 0
    assert vec[3] == 0

    p_slow = Proxy(
        protocol="vmess", address="1.1.1.1", port=443, latency=600.0, config="conf2"
    )
    vec_slow = _compute_vector(p_slow)
    assert vec_slow[2] == 2  # Slow bucket
    assert vec_slow[3] == 3  # 443 % 10


def test_generate_vectors(tmp_path):
    p1 = Proxy(protocol="ss", address="1.1.1.1", port=80, is_working=True, config="c1")
    p2 = Proxy(protocol="ss", address="2.2.2.2", port=80, is_working=False, config="c2")

    generate_vectors([p1, p2], tmp_path)

    output = tmp_path / "vectors.json"
    assert output.exists()

    data = json.loads(output.read_text())
    assert len(data) == 1
    assert p1.id in data
    assert p2.id not in data
    assert len(data[p1.id]) == 8


def test_generate_vectors_error(tmp_path):
    p1 = Proxy(protocol="ss", address="1.1.1.1", port=80, is_working=True, config="c1")

    with patch(
        "configstream.utils.AtomicFileWriter.write_text",
        side_effect=Exception("Fail"),
    ):
        generate_vectors([p1], tmp_path)  # Should log error but not crash
