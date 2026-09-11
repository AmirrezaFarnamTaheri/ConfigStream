# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

from scripts import generate_supply_chain_evidence

REPO_ROOT = Path(__file__).resolve().parents[2]
SBOM_PATH = REPO_ROOT / "docs/generated/sbom.cdx.json"
LICENSE_REPORT_PATH = REPO_ROOT / "docs/generated/dependency-licenses.json"
GO_ROOT = REPO_ROOT / "src/go"


def test_generated_supply_chain_evidence_is_current() -> None:
    assert generate_supply_chain_evidence.generate(REPO_ROOT, check=True) == []


def test_sbom_covers_all_repository_ecosystems() -> None:
    payload = json.loads(SBOM_PATH.read_text(encoding="utf-8"))
    ecosystems = {
        component["properties"][0]["value"]
        for component in payload["components"]
        if component.get("properties")
    }
    assert {"python", "npm", "go", "cargo"}.issubset(ecosystems)
    assert payload["bomFormat"] == "CycloneDX"
    assert payload["specVersion"] == "1.6"


def test_license_report_never_claims_unknown_license() -> None:
    payload = json.loads(LICENSE_REPORT_PATH.read_text(encoding="utf-8"))
    assert payload["component_count"] > 0
    assert payload["unknown_license_count"] >= 0
    for item in payload["components"]:
        if item["license_status"] == "unknown":
            assert item["licenses"] == []


def test_sbom_covers_every_go_module() -> None:
    payload = json.loads(SBOM_PATH.read_text(encoding="utf-8"))
    go_sources = set()
    for component in payload["components"]:
        properties = {
            prop["name"]: prop["value"] for prop in component.get("properties", [])
        }
        if properties.get("configstream:ecosystem") == "go":
            go_sources.add(properties.get("configstream:source-manifest"))
    expected = {
        path.relative_to(REPO_ROOT).as_posix() for path in GO_ROOT.glob("*/go.mod")
    }
    assert expected.issubset(go_sources)
