
import pytest
import json
from pathlib import Path
from src.configstream.intelligence.vectors import generate_vectors, _compute_vector
from src.configstream.models import Proxy
from unittest.mock import patch

def test_compute_vector():
    p = Proxy(
        config="ss://test",
        protocol="shadowsocks",
        address="1.2.3.4",
        port=443,
        country_code="US",
        latency=100,
        org="Google",
    )
    vec = _compute_vector(p)
    assert len(vec) == 8
    assert vec[2] == 0 # Latency bucket 0 (<150)

    p.latency = 300
    vec = _compute_vector(p)
    assert vec[2] == 1 # Latency bucket 1 (<500)

    p.latency = 1000
    vec = _compute_vector(p)
    assert vec[2] == 2 # Latency bucket 2 (>=500)

def test_generate_vectors(tmp_path):
    proxies = [
        Proxy(config="ss://1", protocol="ss", address="1.1.1.1", port=80, is_working=True),
        Proxy(config="ss://2", protocol="ss", address="2.2.2.2", port=80, is_working=False) # Skipped
    ]
    generate_vectors(proxies, tmp_path)

    output_file = tmp_path / "vectors.json"
    assert output_file.exists()
    data = json.loads(output_file.read_text())
    assert len(data) == 1
    assert proxies[0].id in data

def test_generate_vectors_exception():
    proxies = [Proxy(config="ss://1", protocol="ss", address="1.1.1.1", port=80, is_working=True)]

    # Mock write_text to raise exception
    with patch("src.configstream.utils.AtomicFileWriter.write_text") as mock_write:
        mock_write.side_effect = Exception("Disk full")
        # Should catch exception and log error, not crash
        generate_vectors(proxies, Path("/tmp"))
