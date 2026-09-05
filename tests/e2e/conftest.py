# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared browser selection and availability checks for every E2E module."""

import os
from pathlib import Path

import pytest
from tests.browser_support import configured_browser_options


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args: dict) -> dict:
    return {**browser_type_launch_args, **configured_browser_options()}


@pytest.fixture(autouse=True)
def require_browser(request):
    # Mock-only tests do not need a browser installation.
    if "page" not in request.fixturenames:
        return
    options = configured_browser_options()
    playwright = request.getfixturevalue("playwright")
    if not options and not Path(playwright.chromium.executable_path).is_file():
        message = "Playwright browser unavailable; install the pinned browser or set PLAYWRIGHT_CHROMIUM_EXECUTABLE"
        if os.getenv("CONFIGSTREAM_REQUIRE_PLAYWRIGHT") == "1":
            pytest.fail(message)
        pytest.skip("Playwright browser unavailable; install the pinned browser")
