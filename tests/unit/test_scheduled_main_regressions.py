# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from configstream.generators.singbox import SingBoxGenerator

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_singbox_generator_does_not_emit_removed_rcode_dns_server() -> None:
    dns = SingBoxGenerator().generate([])["dns"]

    assert all(
        not str(server.get("address", "")).startswith("rcode://")
        for server in dns["servers"]
    )
    assert any(
        rule.get("action") == "predefined"
        and rule.get("rcode") == "NOERROR"
        and "geosite-category-ads-all" in rule.get("rule_set", [])
        for rule in dns["rules"]
    )


def test_dynamic_reshard_direct_script_resolves_stage_evidence_import(
    tmp_path: Path,
) -> None:
    script = REPO_ROOT / "scripts" / "dynamic_reshard.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "ModuleNotFoundError" not in combined
    assert "No module named 'scripts'" not in combined
