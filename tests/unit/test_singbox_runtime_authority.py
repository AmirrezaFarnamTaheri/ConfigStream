# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path


def test_legacy_tester_is_not_release_authority() -> None:
    runtime = json.loads(
        Path("config/runtime-versions.json").read_text(encoding="utf-8")
    )
    sing_box = runtime["sing_box"]

    assert sing_box["embedded_tester"] != sing_box["release_validator"]
    assert sing_box["release_authority"] == "native-validator-only"
    assert "pre-release-connectivity-screen-only" in sing_box["embedded_contract"]
    assert "release-validator conformance" in sing_box["embedded_contract"]


def test_release_artifacts_are_checked_by_governed_native_sing_box() -> None:
    native_checks = Path("scripts/native_client_checks.py").read_text(encoding="utf-8")
    main_workflow = Path(".github/workflows/main.yml").read_text(encoding="utf-8")
    runtime = json.loads(
        Path("config/runtime-versions.json").read_text(encoding="utf-8")
    )

    assert '[str(singbox_binary), "check", "-c", str(path)]' in native_checks
    assert "native_client_checks.py" in main_workflow
    assert runtime["sing_box"]["release_validator"] in main_workflow
