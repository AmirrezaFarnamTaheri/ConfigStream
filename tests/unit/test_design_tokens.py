# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for Cold Luxury design tokens, sticky header scroll-margin, and focus-visible styling."""

from __future__ import annotations

import re
from pathlib import Path

CSS_PATH = (
    Path(__file__).resolve().parents[2] / "frontend" / "assets" / "css" / "style.css"
)


def test_design_tokens_present() -> None:
    """Verify that Cold Luxury design tokens are defined in style.css."""
    assert CSS_PATH.exists(), f"{CSS_PATH} does not exist"
    css_content = CSS_PATH.read_text(encoding="utf-8")

    expected_tokens = [
        ("--bg-base", "#0a0e17"),
        ("--bg-surface", "#111827"),
        ("--bg-glass", "rgba(255, 255, 255, 0.78)"),
        ("--border-subtle", "rgba(255, 255, 255, 0.08)"),
        ("--border-focus", "#06b6d4"),
        ("--accent-cobalt", "#3b82f6"),
        ("--accent-cyan", "#06b6d4"),
    ]

    for token_name, token_val in expected_tokens:
        pattern = rf"{token_name}\s*:\s*{re.escape(token_val)}"
        assert (
            re.search(pattern, css_content) is not None
        ), f"Expected design token '{token_name}: {token_val}' in {CSS_PATH}"


def test_sticky_header_scroll_margin_offset() -> None:
    """Verify that scroll-margin-top is declared for section targets / hash anchors to prevent header clipping."""
    css_content = CSS_PATH.read_text(encoding="utf-8")

    assert (
        "scroll-margin-top" in css_content
    ), "Missing scroll-margin-top declaration in style.css"

    # Verify that scroll-margin-top is set to at least 80px or uses --header-height
    scroll_margin_match = re.search(
        r"scroll-margin-top\s*:\s*(80px|calc\([^)]+\))",
        css_content,
    )
    assert (
        scroll_margin_match is not None
    ), "scroll-margin-top must be set to 80px or calc(var(--header-height, 64px) + 16px)"

    # Check that target selectors include section[id], div[id], or explicit anchor sections
    assert (
        re.search(
            r"(section\[id\]|#faq|#quick-search|#telemetry|#features|#download|\[id\])",
            css_content,
        )
        is not None
    ), "scroll-margin-top should target section IDs or anchor destinations"


def test_focus_visible_high_contrast_outline() -> None:
    """Verify that :focus-visible enforces high-contrast 2px outline and outline-offset."""
    css_content = CSS_PATH.read_text(encoding="utf-8")

    assert ":focus-visible" in css_content, "Missing :focus-visible rules in style.css"

    # Verify 2px outline and border-focus / cyan outline
    assert (
        re.search(
            r"outline\s*:\s*2px\s+solid\s+(var\(--border-focus\)|#06b6d4)",
            css_content,
        )
        is not None
    ), "Expected :focus-visible outline: 2px solid var(--border-focus) or #06b6d4"

    # Verify outline-offset
    assert (
        re.search(
            r"outline-offset\s*:\s*2px",
            css_content,
        )
        is not None
    ), "Expected outline-offset: 2px for focus indicators"
