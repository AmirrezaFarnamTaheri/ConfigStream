# SPDX-License-Identifier: AGPL-3.0-or-later
"""One-shot exact-anchor patch for the last verified PR #593 review findings."""
from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"anchor not found in {path}: {old[:120]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


# Slipstream remains strict when requested, but unsupported platforms can start
# and use the ordinary DNS scanner without resolving an unavailable binary.
replace_once(
    "src/configstream/tools/dns_scanner/python/dnsscanner_tui.py",
    '''    def get_platform_key(self) -> str:\n        """Return an architecture-specific key present in the pinned manifest."""\n''',
    '''    def is_supported(self) -> bool:\n        """Return whether this platform has a pinned Slipstream artifact."""\n        return f"{self.system}-{self.machine}" in self.ARTIFACTS\n\n    def get_platform_key(self) -> str:\n        """Return an architecture-specific key present in the pinned manifest."""\n''',
)
replace_once(
    "src/configstream/tools/dns_scanner/python/dnsscanner_tui.py",
    '''        self.slipstream_manager = SlipstreamManager()\n        self.slipstream_path = str(self.slipstream_manager.get_executable_path())\n        self.slipstream_domain = ""\n''',
    '''        self.slipstream_manager = SlipstreamManager()\n        self.slipstream_path = ""\n        self.slipstream_domain = ""\n''',
)
replace_once(
    "src/configstream/tools/dns_scanner/python/dnsscanner_tui.py",
    '''        # Check if slipstream needs to be downloaded\n        if self.test_slipstream and not self.slipstream_manager.is_installed():\n            self.notify(\n                "Slipstream not found. Starting download...", severity="information"\n            )\n            self.run_worker(self._download_and_start_scan(), exclusive=True)\n            return\n''',
    '''        # Resolve Slipstream only when the optional proxy test is requested.\n        if self.test_slipstream:\n            if not self.slipstream_manager.is_supported():\n                self.notify(\n                    f"Slipstream is unsupported on {self.slipstream_manager.system} "\n                    f"{self.slipstream_manager.machine}",\n                    severity="error",\n                )\n                return\n            if self.slipstream_manager.is_installed():\n                self.slipstream_path = str(\n                    self.slipstream_manager.get_executable_path()\n                )\n            else:\n                self.notify(\n                    "Slipstream not found. Starting download...",\n                    severity="information",\n                )\n                self.run_worker(self._download_and_start_scan(), exclusive=True)\n                return\n''',
)

# Strict annotations for the still-live sites in the consolidated review.
replace_once(
    "tests/unit/test_backup_extended.py",
    '''def test_restore_rejects_oversized_gzip_before_publication(\n    data_dir, backup_dir, monkeypatch\n):\n''',
    '''def test_restore_rejects_oversized_gzip_before_publication(\n    data_dir: Path, backup_dir: Path, monkeypatch: pytest.MonkeyPatch\n) -> None:\n''',
)
replace_once(
    "tests/unit/test_cache_paths.py",
    '''from unittest.mock import patch\n\nfrom configstream.test_cache import TestResultCache\n''',
    '''from pathlib import Path\nfrom unittest.mock import patch\n\nimport pytest\n\nfrom configstream.test_cache import TestResultCache\n''',
)
replace_once(
    "tests/unit/test_cache_paths.py",
    '''def test_oversized_cache_file_fails_empty(tmp_path, monkeypatch):\n''',
    '''def test_oversized_cache_file_fails_empty(\n    tmp_path: Path, monkeypatch: pytest.MonkeyPatch\n) -> None:\n''',
)
replace_once(
    "tests/unit/test_cli_extended.py",
    '''def test_update_databases_rejects_pinned_mirror_digest_mismatch(runner):\n''',
    '''def test_update_databases_rejects_pinned_mirror_digest_mismatch(\n    runner: CliRunner,\n) -> None:\n''',
)
replace_once(
    "tests/unit/test_publication_policy.py",
    '''import json\nfrom datetime import datetime, timedelta, timezone\n\nimport pytest\n''',
    '''import json\nfrom datetime import datetime, timedelta, timezone\nfrom pathlib import Path\n\nimport pytest\n''',
)
replace_once(
    "tests/unit/test_publication_policy.py",
    '''def test_sanitized_event_stream_is_public_when_allowlisted(tmp_path):\n''',
    '''def test_sanitized_event_stream_is_public_when_allowlisted(tmp_path: Path) -> None:\n''',
)

lifecycle = "tests/unit/test_dnsscanner_tui_lifecycle.py"
replace_once(
    lifecycle,
    '''import pytest\n\nfrom configstream.tools.dns_scanner.python.dnsscanner_lifecycle import (\n''',
    '''import pytest\n\nfrom configstream.tools.dns_scanner.python import dnsscanner_tui\nfrom configstream.tools.dns_scanner.python.dnsscanner_lifecycle import (\n''',
)
for old, new in (
    ("async def test_cancel_and_await_tasks_runs_task_finalizers():", "async def test_cancel_and_await_tasks_runs_task_finalizers() -> None:"),
    ("    async def worker():", "    async def worker() -> None:"),
    ("async def test_kill_and_reap_processes_waits_for_children():", "async def test_kill_and_reap_processes_waits_for_children() -> None:"),
    ("        def __init__(self):", "        def __init__(self) -> None:"),
    ("        def kill(self):", "        def kill(self) -> None:"),
    ("        async def wait(self):", "        async def wait(self) -> int:"),
    ("async def test_kill_and_reap_processes_reaps_already_exited_child():", "async def test_kill_and_reap_processes_reaps_already_exited_child() -> None:"),
):
    replace_once(lifecycle, old, new)

# The second Process class contains the same method anchors; replace_once sees
# the typed first instance, so handle the remaining untyped definitions directly.
target = Path(lifecycle)
text = target.read_text(encoding="utf-8")
text = text.replace("        def __init__(self):", "        def __init__(self) -> None:")
text = text.replace("        def kill(self):", "        def kill(self) -> None:")
text = text.replace("        async def wait(self):", "        async def wait(self) -> int:")
target.write_text(text, encoding="utf-8")

# Regression: constructing the TUI on a platform without a pinned Slipstream
# artifact must not resolve the binary eagerly or raise.
with target.open("a", encoding="utf-8") as handle:
    handle.write(\
'''\n\ndef test_tui_initialization_defers_unsupported_slipstream_resolution(\n    monkeypatch: pytest.MonkeyPatch,\n) -> None:\n    monkeypatch.setattr(dnsscanner_tui.platform, "system", lambda: "Linux")\n    monkeypatch.setattr(dnsscanner_tui.platform, "machine", lambda: "armv7l")\n\n    app = dnsscanner_tui.DNSScannerTUI()\n\n    assert app.slipstream_manager.is_supported() is False\n    assert app.slipstream_path == ""\n''')
