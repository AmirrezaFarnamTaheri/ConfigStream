# SPDX-License-Identifier: AGPL-3.0-or-later
"""Accessible-name checks for static frontend form controls."""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2] / "frontend"


def _has_accessible_name(soup: BeautifulSoup, control) -> bool:
    if control.get("aria-label") or control.get("aria-labelledby") or control.get("title"):
        return True
    control_id = control.get("id")
    if control_id and soup.find("label", attrs={"for": control_id}):
        return True
    return control.find_parent("label") is not None


def test_all_static_form_controls_have_accessible_names() -> None:
    failures: list[str] = []
    for path in sorted(ROOT.glob("*.html")):
        if path.name == "lab-offline.html":
            continue  # dynamic controls receive programmatic labels.
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        for control in soup.find_all(["input", "select", "textarea", "button"]):
            if control.name == "button" and control.get_text(strip=True):
                continue
            if not _has_accessible_name(soup, control):
                failures.append(f"{path.name}: {str(control)[:120]}")
    assert failures == []
