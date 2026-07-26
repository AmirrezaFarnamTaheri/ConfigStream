# SPDX-License-Identifier: AGPL-3.0-or-later
"""Apply focused fixes for cross-client contract integration regressions."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path_name: str, old: str, new: str) -> None:
    path = ROOT / path_name
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path_name}: expected one anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    replace_once(
        "scripts/validate_output_matrix.py",
        '''CLIENT_CONFIG_FAMILIES = {
    "chains",
    "clash",
    "singbox",
    "singbox-vpn",
}
VALID_CORE_FORMATS = {
    "clash",
    "sing-box",
}
''',
        '''CLIENT_CONFIG_FAMILIES = {
    "chains",
    "clash",
    "singbox",
    "singbox-vpn",
    "xray",
}
VALID_CORE_FORMATS = {
    "clash",
    "sing-box",
    "xray",
}
''',
    )

    replace_once(
        "src/configstream/output/singbox_contract.py",
        '''    elif detour not in tags:
        errors.append(f"{location} references unknown detour: {detour}")
''',
        '''    elif detour not in tags:
        item_kind = "endpoint" if " endpoints[" in location else "outbound"
        file_name = location.split(" ", 1)[0]
        errors.append(f"{file_name} unknown {item_kind} detour: {detour}")
''',
    )

    replace_once(
        "scripts/finalize_release_outputs.py",
        '''        outbound["outbounds"] = unique
        if outbound.get("default") not in unique:
            outbound.pop("default", None)
''',
        '''        if not unique and "direct" in known:
            unique = ["direct"]
        outbound["outbounds"] = unique
        if outbound.get("default") not in unique:
            outbound.pop("default", None)
''',
    )

    replace_once(
        "tests/unit/test_validate_pages_artifact.py",
        '''        elif rel_path.startswith("clash") and rel_path.endswith(".yaml"):
            _write_text(path, _clash_payload())
        elif rel_path.endswith(".json"):
            _write_text(path, "{}")
        else:
            _write_text(path)
''',
        '''        elif rel_path.startswith("clash") and rel_path.endswith(".yaml"):
            _write_text(path, _clash_payload())
        elif rel_path == "xray.json":
            _write_text(
                path,
                json.dumps(
                    {
                        "outbounds": [
                            {"tag": "direct", "protocol": "freedom", "settings": {}},
                            {"tag": "block", "protocol": "blackhole", "settings": {}},
                        ],
                        "routing": {"rules": []},
                    }
                ),
            )
        elif rel_path in {
            "proxies.txt",
            "proxies-dns-safe.txt",
            "proxies-dns-hardened.txt",
            "base64.txt",
            "base64-dns-safe.txt",
            "base64-dns-hardened.txt",
        }:
            _write_text(path, "")
        elif rel_path.endswith(".json"):
            _write_text(path, "{}")
        else:
            _write_text(path)
''',
    )

    replace_once(
        "tests/unit/test_validate_pages_artifact.py",
        '''def test_write_pages_contract_refreshes_mutated_artifact(tmp_path: Path) -> None:
    _write_valid_artifact(tmp_path)
    _write_text(tmp_path / "base64.txt", "changed after initial manifest")
''',
        '''def test_write_pages_contract_refreshes_mutated_artifact(tmp_path: Path) -> None:
    _write_valid_artifact(tmp_path)
    updated_subscription = "ss://changed@example.com:443#manifest-refresh\\n"
    _write_text(tmp_path / "proxies.txt", updated_subscription)
    _write_text(
        tmp_path / "base64.txt",
        base64.b64encode(updated_subscription.encode("utf-8")).decode("ascii"),
    )
''',
    )

    replace_once(
        "tests/unit/test_output.py",
        '''from scripts.validate_pages_artifact import validate_pages_artifact
''',
        '''from scripts.finalize_release_outputs import finalize
from scripts.validate_pages_artifact import validate_pages_artifact
''',
    )
    replace_once(
        "tests/unit/test_output.py",
        '''    save_metadata(stats, proxies, tmp_path)

    api_dir = tmp_path / "api"
''',
        '''    save_metadata(stats, proxies, tmp_path)
    finalize(tmp_path, tmp_path, 0.0)

    api_dir = tmp_path / "api"
''',
    )
    replace_once(
        "tests/unit/test_output.py",
        '''    api_dir = tmp_path / "api"
    api_dir.mkdir()
''',
        '''    api_dir = tmp_path / "api"
    api_dir.mkdir(exist_ok=True)
''',
    )

    replace_once(
        "tests/unit/test_output_generators.py",
        '''    # Revival chains should survive Clash generation via relay/dialer-proxy links.
    assert "dialer-proxy:" in output
    assert "type: relay" in output
''',
        '''    # Revival chains use Mihomo dialer-proxy links without deprecated relay groups.
    assert "dialer-proxy:" in output
    assert "type: relay" not in output
    assert "Revived Chain-warp" in output
''',
    )

    for path in (
        ROOT / ".github/workflows/fix-client-contract-regressions.yml",
        ROOT / "scripts/fix_client_contract_regressions.py",
    ):
        path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
