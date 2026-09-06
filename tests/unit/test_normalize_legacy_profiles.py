# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

from scripts.normalize_legacy_profiles import normalize_profiles


def _working_http_record() -> dict[str, object]:
    return {
        "id": "http-1",
        "protocol": "http",
        "address": "203.0.113.10",
        "port": 8080,
        "is_working": True,
        "remarks": "working-http",
        "details": {},
    }


def test_normalizer_preserves_dns_variant_bytes(tmp_path: Path) -> None:
    (tmp_path / "proxies.json").write_text(
        json.dumps([_working_http_record()]), encoding="utf-8"
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
    assert "[General]" in (tmp_path / "surge.conf").read_text(encoding="utf-8")
    assert "[Proxy Group]" in (tmp_path / "loon.conf").read_text(encoding="utf-8")
    assert "http=working-http" in (tmp_path / "quantumult.conf").read_text(
        encoding="utf-8"
    )
    assert report["profiles"]["surge"]["preserved_variants"] == [
        "surge-dns-hardened.conf"
    ]
    assert report["profiles"]["loon"]["preserved_variants"] == [
        "loon-dns-hardened.conf"
    ]
    assert report["profiles"]["quantumult"]["preserved_variants"] == [
        "quantumult-dns-hardened.conf"
    ]
