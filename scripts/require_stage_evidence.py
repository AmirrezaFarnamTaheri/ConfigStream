# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fail closed unless one resilient stage and its evidence are release-ready."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from scripts.resilient_stage import DEFAULT_REPORT_DIR, evaluate_readiness


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--required-file", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    result = evaluate_readiness(
        args.report_dir,
        [args.stage],
        args.required_file,
        args.output,
    )
    if not result["publish_ready"]:
        print(f"ERROR: prerequisite stage {args.stage!r} is not release-ready")
        return 1
    print(f"OK: prerequisite stage {args.stage!r} and evidence are release-ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
