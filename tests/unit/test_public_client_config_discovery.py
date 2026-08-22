# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

from scripts.finalize_release_outputs import finalize, modernize_singbox
from scripts.public_client_configs import (
    discover_mihomo_configs,
    discover_singbox_configs,
)


def _write(path: Path, content: str = "{}") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _relative(root: Path, paths: list[Path]) -> list[str]:
    return [path.relative_to(root).as_posix() for path in paths]


def test_discovers_every_public_full_client_config_and_excludes_record_lists(
    tmp_path: Path,
) -> None:
    for relative in (
        "singbox.json",
        "singbox-dns-safe.json",
        "chains.json",
        "countries/IR.json",
        "protocols/vless.json",
        "chosen/singbox.json",
        "countries/IR.list.json",
        "protocols/vless.list.json",
    ):
        _write(tmp_path / relative)
    for relative in ("clash.yaml", "clash-dns-safe.yaml", "chosen/clash.yaml"):
        _write(tmp_path / relative, "proxies: []\n")

    assert _relative(tmp_path, discover_singbox_configs(tmp_path)) == [
        "chains.json",
        "chosen/singbox.json",
        "countries/IR.json",
        "protocols/vless.json",
        "singbox-dns-safe.json",
        "singbox.json",
    ]
    assert _relative(tmp_path, discover_mihomo_configs(tmp_path)) == [
        "chosen/clash.yaml",
        "clash-dns-safe.yaml",
        "clash.yaml",
    ]


def test_nested_singbox_payload_uses_same_modernization_contract() -> None:
    payload = {
        "outbounds": [
            {"type": "block", "tag": "block"},
            {"type": "dns", "tag": "dns-out"},
            {"type": "direct", "tag": "direct"},
        ]
    }

    modern = modernize_singbox(json.loads(json.dumps(payload)))

    assert modern["outbounds"] == [{"type": "direct", "tag": "direct"}]


def test_finalizer_modernizes_nested_public_singbox_configs(tmp_path: Path) -> None:
    output = tmp_path / "output"
    legacy = {
        "outbounds": [
            {"type": "block", "tag": "block"},
            {"type": "dns", "tag": "dns-out"},
            {"type": "direct", "tag": "direct"},
        ]
    }
    _write(output / "proxies.json", "[]")
    _write(output / "metadata.json", "{}")
    _write(output / "countries/IR.json", json.dumps(legacy))
    _write(output / "protocols/vless.json", json.dumps(legacy))
    _write(output / "chosen/singbox.json", json.dumps(legacy))

    finalize(output, tmp_path, 0.8)

    for relative in (
        "countries/IR.json",
        "protocols/vless.json",
        "chosen/singbox.json",
    ):
        payload = json.loads((output / relative).read_text(encoding="utf-8"))
        assert payload["outbounds"] == [{"type": "direct", "tag": "direct"}]
