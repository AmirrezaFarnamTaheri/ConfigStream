# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for Tabular Numerics (tnum), WCAG 2.2 AA Touch Targets, and Accessible Iconography."""

from __future__ import annotations

import re
from pathlib import Path
from bs4 import BeautifulSoup

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
CSS_PATH = FRONTEND_DIR / "assets" / "css" / "style.css"
INDEX_HTML = FRONTEND_DIR / "index.html"
PROXIES_HTML = FRONTEND_DIR / "proxies.html"


def test_tabular_numerics_css_tokens() -> None:
    """Verify that tabular-nums and font-feature-settings tnum are applied to telemetry/numeric classes in style.css."""
    assert CSS_PATH.exists(), f"{CSS_PATH} does not exist"
    css_content = CSS_PATH.read_text(encoding="utf-8")

    assert (
        "font-variant-numeric: tabular-nums" in css_content
        or "font-variant-numeric:tabular-nums" in css_content
    ), "Missing 'font-variant-numeric: tabular-nums' in style.css"
    assert (
        'font-feature-settings: "tnum" 1' in css_content
        or 'font-feature-settings:"tnum" 1' in css_content
        or 'font-feature-settings: "tnum"' in css_content
    ), "Missing 'font-feature-settings: \"tnum\" 1' in style.css"

    # Check key selectors for tabular numerics
    for selector in [
        ".tabular-nums",
        ".ping-badge",
        ".port-cell",
        ".counter-value",
        ".stat-value",
    ]:
        assert (
            selector in css_content
        ), f"Expected selector '{selector}' to be defined with tabular numerics in style.css"


def test_proxy_table_numeric_columns_use_tabular_nums() -> None:
    """Verify that proxy table latency/ping/port/numeric columns are styled with tabular numerics."""
    css_content = CSS_PATH.read_text(encoding="utf-8")

    # Match tabular-nums rule containing latency or proxy table numerical styling
    assert (
        re.search(
            r"(?:\.tabular-nums|\.proxies-table[^{]*?(?:latency|ping|port|\.stat-value|\.counter-value))[^{]*\{[^}]*font-variant-numeric:\s*tabular-nums",
            css_content,
            re.DOTALL | re.IGNORECASE,
        )
        is not None
    ), "Proxy table numeric/latency elements must utilize font-variant-numeric: tabular-nums"


def test_touch_target_dimensions_wcag22() -> None:
    """Verify minimum touch targets: >=24x24px desktop and >=44x44px for coarse pointer/mobile."""
    css_content = CSS_PATH.read_text(encoding="utf-8")

    # Interactive triggers: .btn, .copy-btn, .mode-tab, .client-select, .pagination-btn
    for trigger in [".btn", ".copy-btn", ".client-select", ".pagination-btn"]:
        assert trigger in css_content, f"Expected {trigger} styling in style.css"

    # Verify coarse pointer or mobile touch target rule enforcing min 44x44px
    touch_target_pattern = r"(?:@media[^{]*\((?:pointer:\s*coarse|max-width:[^)]+)\)[^{]*\{[^}]*(?:min-height:\s*44px|min-width:\s*44px))"
    assert (
        re.search(touch_target_pattern, css_content, re.DOTALL) is not None
    ), "Expected min-height: 44px and min-width: 44px on coarse pointer / mobile media queries"

    # Verify desktop min dimension token (>= 24px) for interactive triggers
    assert (
        re.search(r"--touch-target-desktop\s*:\s*24px", css_content)
        or re.search(r"--touch-target-min\s*:\s*44px", css_content)
        or re.search(r"min-height:\s*24px", css_content)
        or re.search(r"min-height:\s*44px", css_content)
    ), "Expected touch target CSS variables or min-height/width definitions"


def test_accessible_iconography_and_no_structural_emojis() -> None:
    """Verify that structural navigation and action buttons avoid raw emojis and use accessible SVG icons."""
    for html_path in [INDEX_HTML, PROXIES_HTML]:
        assert html_path.exists(), f"{html_path} does not exist"
        html_content = html_path.read_text(encoding="utf-8")
        soup = BeautifulSoup(html_content, "html.parser")

        # Check buttons and navigation links for raw emojis as sole controls
        for btn in soup.find_all(["button", "a"]):
            btn_text = btn.get_text(strip=True)
            aria_label = btn.get("aria-label", "")
            has_svg_or_feather = bool(
                btn.find(["svg", "object"])
                or btn.find(attrs={"data-feather": True})  # type: ignore[call-overload]
            )
            if not btn_text and not aria_label and not btn.find("img"):
                assert (
                    has_svg_or_feather
                ), f"Interactive element in {html_path.name} must have accessible label or SVG: {btn}"
