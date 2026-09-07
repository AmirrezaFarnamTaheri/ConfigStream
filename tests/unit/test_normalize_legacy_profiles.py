# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.normalize_legacy_profiles import normalize_profiles, values


def _working_record(address: str, protocol: str = "http") -> dict[str, object]:
    record: dict[str, object] = {
        "id": f"{protocol}-1",
        "protocol": protocol,
        "address": address,
        "port": 8080,
        "uuid": "",
        "country": "",
        "country_code": "XX",
        "city": "",
        "asn": "",
        "org": "",
        "latency": 10.0,
        "is_working": True,
        "tags": [],
        "last_checked": "",
        "source": None,
        "security": {},
        "details": {},
        "config": f"{protocol}://{address}:8080",
        "remarks": f"working-{protocol}",
        "process": "native",
    }
    if protocol in {"ss", "shadowsocks"}:
        record["port"] = 8388
        record["details"] = {
            "method": "aes-256-gcm",
            "password": "secret",
        }
        record["config"] = "ss://example"
    return record


def test_normalizer_generates_safe_profiles_and_preserves_hardened_bytes(
    tmp_path: Path,
) -> None:
    standard_records = [_working_record("proxy.example")]
    safe_records = [
        _working_record("203.0.113.10"),
        _working_record("198.51.100.20", "shadowsocks"),
    ]
    (tmp_path / "proxies.json").write_text(
        json.dumps(standard_records), encoding="utf-8"
    )
    (tmp_path / "proxies-dns-safe.json").write_text(
        json.dumps(safe_records), encoding="utf-8"
    )
    (tmp_path / "proxies-dns-safe.txt").write_text(
        "http://203.0.113.10:8080\nss://safe\n", encoding="utf-8"
    )
    hardened = {
        "surge-dns-hardened.conf": "# hardened surge\n[DNS]\ndns-server = https://dns.example/dns-query\n",
        "loon-dns-hardened.conf": "# hardened loon\n[DNS]\ndns-server = tls://1.1.1.1\n",
        "quantumult-dns-hardened.conf": "# hardened qx\n[dns]\nserver=https://dns.example/dns-query\n",
    }
    for filename, content in hardened.items():
        (tmp_path / filename).write_text(content, encoding="utf-8")

    report = normalize_profiles(tmp_path)

    for filename, content in hardened.items():
        assert (tmp_path / filename).read_text(encoding="utf-8") == content
    for filename in (
        "surge-dns-safe.conf",
        "loon-dns-safe.conf",
        "quantumult-dns-safe.conf",
    ):
        content = (tmp_path / filename).read_text(encoding="utf-8")
        assert "203.0.113.10" in content
        assert "proxy.example" not in content
    assert (tmp_path / "shadowrocket-dns-safe.txt").read_bytes() == (
        tmp_path / "proxies-dns-safe.txt"
    ).read_bytes()
    sip008 = json.loads((tmp_path / "sip008-dns-safe.json").read_text(encoding="utf-8"))
    assert sip008["servers"][0]["server"] == "198.51.100.20"
    assert report["profiles"]["surge"]["dns_safe_file"] == "surge-dns-safe.conf"
    assert report["profiles"]["surge"]["preserved_hardened_file"] == (
        "surge-dns-hardened.conf"
    )
    assert report["dns_safe_aliases"] == {
        "shadowrocket": "shadowrocket-dns-safe.txt",
        "sip008": "sip008-dns-safe.json",
    }


@pytest.mark.parametrize("raw_port", [True, 443.9, float("inf"), float("-inf")])
def test_values_rejects_lossy_or_overflowing_ports(raw_port: object) -> None:
    record = _working_record("203.0.113.30")
    record["port"] = raw_port

    assert values(record) is None


def test_values_accepts_integral_float_port_without_loss() -> None:
    record = _working_record("203.0.113.30")
    record["port"] = 443.0

    parsed = values(record)

    assert parsed is not None
    assert parsed[2] == 443


def test_sip008_skips_malformed_port_without_aborting_other_servers(
    tmp_path: Path,
) -> None:
    valid = _working_record("198.51.100.20", "shadowsocks")
    invalid = _working_record("203.0.113.30", "shadowsocks")
    invalid["port"] = "not-a-port"
    (tmp_path / "proxies.json").write_text(json.dumps([valid]), encoding="utf-8")
    (tmp_path / "proxies-dns-safe.json").write_text(
        json.dumps([invalid, valid]), encoding="utf-8"
    )

    normalize_profiles(tmp_path)

    sip008 = json.loads((tmp_path / "sip008-dns-safe.json").read_text(encoding="utf-8"))
    assert [server["server"] for server in sip008["servers"]] == ["198.51.100.20"]
