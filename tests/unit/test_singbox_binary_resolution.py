import os
import stat
from pathlib import Path

from configstream.testers_core import GoBatchTester


def _make_fake_binary(path: Path):
    path.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def test_binary_found_at_default(tmp_path, monkeypatch):
    bin_path = tmp_path / "configstream-tester"
    _make_fake_binary(bin_path)
    monkeypatch.setenv("CONFIGSTREAM_TESTER_BIN", str(bin_path))

    tester = GoBatchTester()

    assert tester.available is True
    assert tester.binary_path == str(bin_path)


def test_binary_found_via_path(monkeypatch, tmp_path):
    bin_path = tmp_path / "configstream-tester"
    _make_fake_binary(bin_path)
    monkeypatch.delenv("CONFIGSTREAM_TESTER_BIN", raising=False)
    # Prepend to PATH so shutil.which can locate it
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}" + os.environ.get("PATH", ""))

    tester = GoBatchTester()

    assert tester.available is True
    assert Path(tester.binary_path).name == "configstream-tester"


def test_binary_missing(monkeypatch):
    monkeypatch.delenv("CONFIGSTREAM_TESTER_BIN", raising=False)
    tester = GoBatchTester(binary_path="/nonexistent/configstream-tester")
    assert tester.available is False
