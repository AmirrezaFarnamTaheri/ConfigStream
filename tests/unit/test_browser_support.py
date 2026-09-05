# SPDX-License-Identifier: AGPL-3.0-or-later
import os
from pathlib import Path

import pytest

from tests.browser_support import configured_browser_options


def test_explicit_browser_overrides_channel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "chromium.exe"
    executable.write_bytes(b"test executable path")
    executable.chmod(0o700)
    monkeypatch.setenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE", str(executable))
    monkeypatch.setenv("PLAYWRIGHT_BROWSER_CHANNEL", "msedge")
    assert configured_browser_options() == {
        "executable_path": str(executable.resolve()),
        "channel": None,
    }


def test_missing_explicit_browser_is_not_silently_replaced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE", str(tmp_path / "missing"))
    with pytest.raises(FileNotFoundError, match="Configured Chromium"):
        configured_browser_options()


@pytest.mark.skipif(os.name == "nt", reason="POSIX executable bits are unavailable")
def test_non_executable_browser_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "chromium"
    executable.write_bytes(b"not executable")
    executable.chmod(0o600)
    monkeypatch.setenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE", str(executable))
    with pytest.raises(FileNotFoundError, match="Configured Chromium"):
        configured_browser_options()


def test_default_uses_managed_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE", raising=False)
    monkeypatch.delenv("PLAYWRIGHT_BROWSER_CHANNEL", raising=False)
    assert configured_browser_options() == {}
