# SPDX-License-Identifier: AGPL-3.0-or-later
"""Static parity checks for Laboratory chain strategies."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


def _strategy_ids() -> list[str]:
    payload = json.loads(_read("frontend/assets/data/lab_strategies.json"))
    return [str(item["id"]) for item in payload["strategies"]]


def test_lab_strategy_manifest_matches_html_options_and_js_hints() -> None:
    strategy_ids = _strategy_ids()
    lab_html = _read("frontend/lab.html")
    lab_js = _read("frontend/assets/js/lab.js")

    html_ids = re.findall(r'<option value="([^"]+)">', lab_html)
    chain_html_ids = html_ids[html_ids.index("warp") : html_ids.index("custom") + 1]
    hint_ids = re.findall(r"'([^']+)':\s*'[^']*'", lab_js.split("const CHAIN_HINTS = {", 1)[1].split("};", 1)[0])

    assert chain_html_ids == strategy_ids
    assert sorted(hint_ids) == sorted(strategy_ids)


def test_lab_strategy_build_path_fails_loudly_for_unknown_strategy() -> None:
    lab_js = _read("frontend/assets/js/lab.js")

    assert "Unsupported chain strategy:" in lab_js
    for strategy_id in _strategy_ids():
        assert strategy_id in lab_js


def test_lab_strategy_count_is_documented_consistently() -> None:
    strategy_count = len(_strategy_ids())

    assert f"{strategy_count} chain strategies" in _read("README.md")
    assert f"Build Chain ({strategy_count} Strategies)" in _read(
        "docs/wiki/project/06-frontend.md"
    )


def test_lab_qr_generation_does_not_use_external_service() -> None:
    lab_js = _read("frontend/assets/js/lab.js")

    assert "api.qrserver.com" not in lab_js
    assert "create-qr-code" not in lab_js
    assert "External QR services are disabled" in lab_js


def test_lab_manual_clean_ip_table_uses_text_nodes() -> None:
    lab_js = _read("frontend/assets/js/lab.js")

    render_table = lab_js.split("function renderCleanIpTable()", 1)[1].split(
        "function populateWarpIpSelect()", 1
    )[0]

    assert "tbody.replaceChildren()" in render_table
    assert "appendTableCell(tr, ip.ip + ':' + ip.port)" in render_table
    assert "td.textContent = String(text)" in render_table
    assert "tr.innerHTML" not in render_table
    assert "parseManualCleanIpLine" in lab_js
    assert "No valid clean IP entries found" in lab_js
