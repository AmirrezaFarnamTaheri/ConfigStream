# SPDX-License-Identifier: AGPL-3.0-or-later
"""Static parity checks for Laboratory chain strategies."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(rel_path: str) -> str:
    path = REPO_ROOT / rel_path
    if rel_path == "frontend/assets/js/lab.js" or path.name == "lab.js":
        # Concatenate all files in the modular lab directory to simulate monolithic lab.js
        lab_dir = REPO_ROOT / "frontend" / "assets" / "js" / "lab"
        contents = []
        # Sort files to ensure deterministic order
        for f in sorted(lab_dir.glob("*.js")):
            contents.append(f.read_text(encoding="utf-8"))
        return "\n\n".join(contents)
    return path.read_text(encoding="utf-8")


def _strategy_ids() -> list[str]:
    payload = json.loads(_read("frontend/assets/data/lab_strategies.json"))
    return [str(item["id"]) for item in payload["strategies"]]


def test_lab_strategy_dynamically_loaded() -> None:
    lab_html = _read("frontend/lab.html")
    lab_js = _read("frontend/assets/js/lab.js")

    assert '<select class="lab-select" id="chainType">' in lab_html
    assert '<option value="warp">WARP Tunnel (Standard)</option>' in lab_html

    assert "fetch(" in lab_js
    assert "lab_strategies.json" in lab_js
    assert "state.strategyManifest[s.id] = s" in lab_js


def test_lab_strategy_static_fallback_matches_manifest() -> None:
    lab_html = _read("frontend/lab.html")
    payload = json.loads(_read("frontend/assets/data/lab_strategies.json"))
    chain_select = lab_html.split('id="chainType"', 1)[1].split("</select>", 1)[0]

    for strategy in payload["strategies"]:
        option = f'<option value="{strategy["id"]}">{strategy["label"]}</option>'
        assert option in chain_select


def test_lab_strategy_schema_is_complete() -> None:
    payload = json.loads(_read("frontend/assets/data/lab_strategies.json"))
    assert payload["schema_version"] == "1.1"
    for s in payload["strategies"]:
        assert "id" in s
        assert "label" in s
        assert "hint" in s
        assert "visual_label" in s
        assert "panels" in s
        assert isinstance(s["panels"], list)
        assert len(s["panels"]) > 0 or s["id"] == "direct"


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
    assert "new QRCode(" in lab_js


def test_lab_manual_clean_ip_table_uses_text_nodes() -> None:
    lab_js = _read("frontend/assets/js/lab.js")

    render_table = lab_js.split("function renderCleanIpTable()", 1)[1].split(
        "function populateWarpIpSelect()", 1
    )[0]

    assert "tbody.replaceChildren()" in render_table
    assert "ip.ip + ':' + ip.port" in render_table
    assert "textContent =" in render_table
    assert "innerHTML" not in render_table
    assert "parseManualCleanIpLine" in lab_js
    assert "No valid clean IP entries found" in lab_js


def test_lab_show_result_dynamic_values_are_escaped() -> None:
    lab_js = _read("frontend/assets/js/lab.js")

    assert "function escapeHtml(value)" in lab_js
    assert "'&': '&amp;'" in lab_js
    assert "'<': '&lt;'" in lab_js
    assert "'>': '&gt;'" in lab_js

    local_proxy = lab_js.split("async function testLocalProxy()", 1)[1].split(
        "// --- Pipeline Proxy Integration ---", 1
    )[0]
    assert "escapeHtml(type)" in local_proxy
    assert "escapeHtml(addr)" in local_proxy
    assert "${type}://${addr}" not in local_proxy

    step1 = lab_js.split("function handleStep1Next()", 1)[1].split(
        "// --- Step 2: Clean IP Discovery ---", 1
    )[0]
    assert "escapeHtml(state.parsedProxy.address)" in step1
    assert "escapeHtml(state.parsedProxy.remark)" in step1

    step3 = lab_js.split("function handleStep3Next()", 1)[1].split(
        "// If local proxy Layer 1 is set", 1
    )[0]
    assert "escapeHtml(e.message)" in step3
    assert "escapeHtml(chainType)" in step3

    step4 = lab_js.split("async function handleStep4Test()", 1)[1].split(
        "function showManualTestInstructions()", 1
    )[0]
    assert "escapeHtml(result.latency || 'N/A')" in step4
    assert "escapeHtml(result.exit_ip)" in step4
    assert "escapeHtml(result.error || 'Unknown error')" in step4


def test_lab_step4_live_manual_modes_are_visible() -> None:
    lab_html = _read("frontend/lab.html")
    lab_js = _read("frontend/assets/js/lab.js")

    assert 'id="step4Mode"' in lab_html
    assert "function updateStep4TestMode()" in lab_js
    assert "Manual test mode." in lab_js
    assert "Live test mode." in lab_js
    assert "Static hosting cannot run server-side proxy tests" in lab_js
    assert "testBtn.textContent = 'Show Manual Test'" in lab_js
    assert "testBtn.textContent = 'Run Live Test'" in lab_js
    assert "protocol === 'file:'" in lab_js
    assert "updateStep4TestMode();" in lab_js


def test_lab_vwarp_metadata_exports() -> None:
    lab_js = _read("frontend/assets/js/lab.js")

    assert (
        r"vwarpComment = `\n# VWARP Metadata: ${JSON.stringify(chainConfig._vwarp)}`;"
        in lab_js
    )
    assert r"xray._vwarp = chainConfig._vwarp;" in lab_js
    assert (
        """const vwarpPrint = chainConfig._vwarp ? `\\n    print("[*] Note: Config uses Vwarp metadata:", CONFIG.get("_vwarp"))` : '';"""
        in lab_js
    )
    assert (
        """const vwarpEcho = chainConfig._vwarp ? `\\necho "[*] Note: Config uses Vwarp metadata: ${JSON.stringify(chainConfig._vwarp).replace(/"/g, '\\\\"')}"` : '';"""
        in lab_js
    )
