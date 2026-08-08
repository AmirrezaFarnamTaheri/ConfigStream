# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

from scripts import generate_dependency_inventory


def test_dependency_inventory_is_current_and_covered() -> None:
    assert generate_dependency_inventory.generate(Path("."), check=True) == []


def test_dependency_inventory_covers_every_manifest_family() -> None:
    payload = json.loads(
        Path("docs/generated/dependency-inventory.json").read_text(encoding="utf-8")
    )
    assert {"python", "npm", "go-tester", "go-utls", "cargo", "container"} == set(
        payload["ecosystems"]
    )
    observed = {
        (item["ecosystem"], item["directory"])
        for item in payload["dependabot_coverage"]
    }
    assert ("docker", "/") in observed
    assert ("gomod", "/src/go/tester") in observed
    assert ("gomod", "/src/go/utls_client") in observed
    assert ("cargo", "/src/rust/ss_checker") in observed


def test_dependency_inventory_includes_optional_and_publisher_entry_points() -> None:
    payload = json.loads(
        Path("docs/generated/dependency-inventory.json").read_text(encoding="utf-8")
    )
    python_items = payload["ecosystems"]["python"]
    observed = {(item["name"].lower(), item.get("scope")) for item in python_items}
    assert ("pytest", "development") in observed
    assert ("huggingface-hub", "publisher") in observed
    assert ("google-api-python-client", "publisher") in observed
