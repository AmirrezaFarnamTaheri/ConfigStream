# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regenerate STATUS.md from the canonical release readiness record."""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.release_state import load_release_state, render_status

ROOT = Path(__file__).resolve().parents[1]
READINESS_PATH = ROOT / "docs" / "readiness.json"
STATUS_PATH = ROOT / "STATUS.md"


def main() -> None:
    state = load_release_state(READINESS_PATH)
    STATUS_PATH.write_text(render_status(state), encoding="utf-8", newline="\n")
    print(
        f"OK: generated {STATUS_PATH.relative_to(ROOT)} from {READINESS_PATH.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
