# SPDX-License-Identifier: AGPL-3.0-or-later
"""Playwright Page Object Model structural test for Laboratory UI."""
import pytest
from unittest.mock import AsyncMock
from tests.e2e.pages.laboratory_page import LaboratoryPage
from playwright.async_api import Page

@pytest.mark.asyncio
async def test_laboratory_page_object_model() -> None:
    mock_page = AsyncMock()
    mock_page.inner_text.return_value = "ConfigStream Laboratory"
    
    lab_page = LaboratoryPage(mock_page)
    await lab_page.navigate("http://localhost:8000")
    
    mock_page.goto.assert_called_once_with("http://localhost:8000")
    assert await lab_page.get_title() == "ConfigStream Laboratory"

@pytest.mark.playwright
def test_laboratory_page_loads(page) -> None:
    """Real browser test: Laboratory page loads without JS runtime errors."""
    import pathlib
    lab_html = pathlib.Path("frontend/lab.html").resolve()
    
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    
    page.goto(f"file://{lab_html}")
    title = page.title()
    assert "Lab" in title or "ConfigStream" in title
    assert len(errors) == 0, f"Page JS errors: {errors}"
