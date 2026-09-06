# SPDX-License-Identifier: AGPL-3.0-or-later
from unittest.mock import patch

from configstream.testers.configured_manager import SingBoxTester


def test_configured_tester_enforces_strict_security_floor(monkeypatch):
    monkeypatch.setenv("STRICT_SECURITY", "true")
    with patch("configstream.testers.manager.GoBatchTester"):
        tester = SingBoxTester(strict_security=False, dry_run=True)
    assert tester.strict_security is True


def test_configured_tester_can_disable_security_via_application_setting(monkeypatch):
    monkeypatch.setenv("STRICT_SECURITY", "false")
    with patch("configstream.testers.manager.GoBatchTester"):
        tester = SingBoxTester(strict_security=False, dry_run=True)
    assert tester.strict_security is False
