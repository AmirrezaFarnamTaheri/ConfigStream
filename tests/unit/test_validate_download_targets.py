# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.validate_download_targets import configured_targets, validate


def _frontend_catalog_source() -> str:
    return Path("frontend/assets/js/dynamic-downloads.js").read_text(encoding="utf-8")


def test_dynamic_catalog_uses_dns_safe_fallback_for_sip008() -> None:
    source = _frontend_catalog_source()
    block = re.search(r"sip008:\s*\{(?P<body>.*?)\n\s*\},", source, re.DOTALL)
    assert block is not None
    body = block.group("body")
    assert 'dnsFile: "sip008-dns-safe.json"' in body
    assert "dnsHardenedFile: null" in body
    assert 'dnsHardenedFile: "sip008-dns-hardened.json"' not in body


def test_validator_rejects_missing_advertised_target(tmp_path: Path) -> None:
    (tmp_path / "assets/js").mkdir(parents=True)
    (tmp_path / "assets/js/dynamic-downloads.js").write_text(
        'const clients = {x: {file: "present.txt", dnsFile: "missing.txt", dnsHardenedFile: null}};\n',
        encoding="utf-8",
    )
    (tmp_path / "index.html").write_text(
        '<a data-file="present.txt">download</a>\n', encoding="utf-8"
    )
    (tmp_path / "present.txt").write_text("ok", encoding="utf-8")

    assert validate(tmp_path) == ["frontend download target is missing: missing.txt"]


def test_validator_requires_manifest_coverage_when_present(tmp_path: Path) -> None:
    (tmp_path / "assets/js").mkdir(parents=True)
    (tmp_path / "assets/js/dynamic-downloads.js").write_text(
        'const clients = {x: {file: "present.txt"}};\n', encoding="utf-8"
    )
    (tmp_path / "index.html").write_text("<main></main>\n", encoding="utf-8")
    (tmp_path / "present.txt").write_text("ok", encoding="utf-8")
    (tmp_path / "artifact_manifest.json").write_text(
        json.dumps({"files": []}), encoding="utf-8"
    )

    assert validate(tmp_path) == [
        "frontend download target omitted from manifest: present.txt"
    ]


def test_configured_targets_rejects_parent_traversal(tmp_path: Path) -> None:
    (tmp_path / "assets/js").mkdir(parents=True)
    (tmp_path / "assets/js/dynamic-downloads.js").write_text(
        'const clients = {x: {file: "../secret.txt"}};\n', encoding="utf-8"
    )
    (tmp_path / "index.html").write_text("<main></main>\n", encoding="utf-8")

    try:
        configured_targets(tmp_path)
    except ValueError as exc:
        assert "unsafe frontend download target" in str(exc)
    else:
        raise AssertionError("expected unsafe target rejection")
