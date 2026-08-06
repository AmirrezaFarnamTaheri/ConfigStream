# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

from scripts import generate_supply_chain_evidence


def test_generated_supply_chain_evidence_is_current() -> None:
    assert generate_supply_chain_evidence.generate(Path("."), check=True) == []


def test_sbom_covers_all_repository_ecosystems() -> None:
    payload = json.loads(Path("docs/generated/sbom.cdx.json").read_text(encoding="utf-8"))
    ecosystems = {
        component["properties"][0]["value"]
        for component in payload["components"]
        if component.get("properties")
    }
    assert {"python", "npm", "go", "cargo"}.issubset(ecosystems)
    assert payload["bomFormat"] == "CycloneDX"
    assert payload["specVersion"] == "1.6"


def test_license_report_never_claims_unknown_license() -> None:
    payload = json.loads(
        Path("docs/generated/dependency-licenses.json").read_text(encoding="utf-8")
    )
    assert payload["component_count"] > 0
    assert payload["unknown_license_count"] >= 0
    for item in payload["components"]:
        if item["license_status"] == "unknown":
            assert item["licenses"] == []
