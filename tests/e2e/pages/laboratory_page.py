# SPDX-License-Identifier: AGPL-3.0-or-later
"""Page Object Model for Frontend Laboratory UI."""
from playwright.sync_api import Page

class LaboratoryPage:
    def __init__(self, page: Page):
        self.page = page
        self.title_selector = "h1"

    def navigate(self, base_url: str):
        self.page.goto(base_url)

    def get_title(self) -> str:
        return self.page.inner_text(self.title_selector)
