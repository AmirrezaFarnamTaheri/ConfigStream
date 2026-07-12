# SPDX-License-Identifier: AGPL-3.0-or-later
"""Apply the one-use PATCH-004/005/006 lifecycle remediation batch."""

from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    outcomes = Path("src/configstream/pipeline/outcomes.py")
    outcomes.write_text(
        '''# SPDX-License-Identifier: AGPL-3.0-or-later
