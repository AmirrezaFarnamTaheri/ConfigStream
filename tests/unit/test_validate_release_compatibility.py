# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_release_compatibility import validate


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    artifact = tmp_path / "output"
    artifact.mkdir(parents=True)
    _write(
        repo / "config/runtime-versions.json",
        {"sing_box": {"release_validator": "1.13.18"}},
    )
    _write(
        artifact / "format_compatibility.json",
        {
            "targets": {
                "sing-box": {"target": "1.13.18"},
                "sip008": {
                    "dns_safe_endpoint_variant": "sip008-dns-safe.json",
                    "dns_hardened_resolver_policy": "unsupported_by_sip008",
                    "dns_hardened_compat_alias": "sip008-dns-hardened.json",
                },
            }
        },
    )
    _write(artifact / "sip008-dns-safe.json", {"version": 1, "servers": []})
    return repo, artifact


def test_release_compatibility_accepts_governed_contract(tmp_path: Path) -> None:
    repo, artifact = _fixture(tmp_path)
    assert validate(artifact, repo) == []


def test_release_compatibility_rejects_stale_sing_box_target(tmp_path: Path) -> None:
    repo, artifact = _fixture(tmp_path)
    payload = json.loads((artifact / "format_compatibility.json").read_text())
    payload["targets"]["sing-box"]["target"] = "1.13.14"
    _write(artifact / "format_compatibility.json", payload)
    assert any(
        "governed release validator" in error for error in validate(artifact, repo)
    )


def test_release_compatibility_rejects_fake_sip008_hardening(tmp_path: Path) -> None:
    repo, artifact = _fixture(tmp_path)
    payload = json.loads((artifact / "format_compatibility.json").read_text())
    payload["targets"]["sip008"]["dns_hardened_resolver_policy"] = "embedded"
    _write(artifact / "format_compatibility.json", payload)
    assert any(
        "resolver policy unsupported" in error for error in validate(artifact, repo)
    )
