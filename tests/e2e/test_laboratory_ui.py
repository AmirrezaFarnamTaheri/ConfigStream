# SPDX-License-Identifier: AGPL-3.0-or-later
"""Playwright Page Object Model structural test for Laboratory UI."""
import pytest
from unittest.mock import MagicMock
from tests.e2e.pages.laboratory_page import LaboratoryPage

def test_laboratory_page_object_model():
    mock_page = MagicMock()
    mock_page.inner_text.return_value = "ConfigStream Laboratory"
    
    lab_page = LaboratoryPage(mock_page)
    lab_page.navigate("http://localhost:8000")
    
    mock_page.goto.assert_called_once_with("http://localhost:8000")
    assert lab_page.get_title() == "ConfigStream Laboratory"
