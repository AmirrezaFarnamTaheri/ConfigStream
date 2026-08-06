# SPDX-License-Identifier: AGPL-3.0-or-later
"""Render blueprint must not promise unsupported shared persistent storage."""

from __future__ import annotations

from pathlib import Path

import yaml


BLUEPRINT = Path(__file__).resolve().parents[2] / "render.yaml"


def test_render_blueprint_is_single_service_and_ephemeral() -> None:
    data = yaml.safe_load(BLUEPRINT.read_text(encoding="utf-8"))
    services = data["services"]
    assert len(services) == 1
    service = services[0]
    assert service["type"] == "web"
    assert "disk" not in service
    assert service.get("plan") == "free"
    assert service["envVars"][0]["key"] == "CONFIGSTREAM_DEPLOYMENT_MODE"
    assert service["envVars"][0]["value"] == "ephemeral-demo"
