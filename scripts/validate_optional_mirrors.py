# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate that optional external mirrors are not documented as core requirements."""

from __future__ import annotations

import sys
from pathlib import Path

ENCODING = "utf-8"
ROOT = Path(__file__).resolve().parents[1]

DOC_FILES = [
    ROOT / "docs/wiki/project/01-introduction.md",
    ROOT / "docs/wiki/project/02-architecture.md",
    ROOT / "docs/wiki/project/05-devops.md",
    ROOT / "docs/wiki/project/Configuration.md",
]

REQUIRED_PHRASES = [
    "GitHub Pages is the core zero-budget publication target",
    "External mirrors are optional",
    "secret-gated",
]

FORBIDDEN_PHRASES = [
    "we have mirrors on GitLab, Hugging Face, and IPFS",
    "we also deploy mirrors to Cloudflare Pages",
    "Daily snapshots of the output directory are pinned to IPFS/IPNS",
    "redirects to IPFS gateways automatically",
]


def validate_optional_mirrors() -> list[str]:
    errors: list[str] = []
    combined = "\n".join(path.read_text(encoding=ENCODING) for path in DOC_FILES)

    for phrase in REQUIRED_PHRASES:
        if phrase not in combined:
            errors.append(f"optional mirror docs missing phrase: {phrase}")

    for phrase in FORBIDDEN_PHRASES:
        if phrase in combined:
            errors.append(
                f"optional mirror docs contain core-capability claim: {phrase}"
            )

    return errors


def main() -> None:
    errors = validate_optional_mirrors()
    if errors:
        print("ERROR: optional mirror documentation validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print("OK: optional mirror documentation validated.")


if __name__ == "__main__":
    main()
