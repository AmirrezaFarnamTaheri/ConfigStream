#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generate/check the deterministic repository source-admission manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_OUTPUT = ROOT / "src" / "configstream" / "data" / "source-admission.json"
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

def batch_sort_key(path: Path) -> tuple[int, str]:
    name = path.stem
    if name.startswith("batch_") and name[6:].isdigit():
        return (int(name[6:]), path.name)
    return (999999, path.name)

from configstream.source_admission import (
    SourceAdmissionError,
    classify_source_locator,
    normalize_source_locator,
)


def source_files() -> list[Path]:
    return sorted((ROOT / "sources").glob("batch_*.txt"), key=batch_sort_key)


def load_urls() -> dict[str, list[str]]:
    origins: dict[str, list[str]] = {}
    for path in source_files():
        for raw in path.read_text(encoding="utf-8").splitlines():
            url = raw.strip()
            if not url or url.startswith("#"):
                continue
            try:
                canonical_url = normalize_source_locator(url)
                classify_source_locator(canonical_url)
            except SourceAdmissionError as exc:
                raise ValueError(
                    f"{path}: invalid fetch source locator: {url!r}: {exc}"
                ) from exc
            if canonical_url != url:
                raise ValueError(
                    f"{path}: non-canonical fetch source locator: {url!r}; "
                    f"use {canonical_url!r}"
                )
            origins.setdefault(canonical_url, []).append(path.relative_to(ROOT).as_posix())
    return origins


def build_payload() -> dict[str, object]:
    origins = load_urls()
    entries = []
    for url in sorted(origins):
        item = classify_source_locator(url)
        item["source_files"] = sorted(origins[url])
        entries.append(item)
    set_digest = hashlib.sha256(
        ("\n".join(sorted(origins)) + "\n").encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": 1,
        "policy": {
            "meaning": "repository-admitted locators; upstream identity remains classified separately",
            "default_enforcement": "fail-closed",
            "allowed_schemes": ["https", "http"],
            "blocked_trust_classes": ["insecure-transport"],
        },
        "source_files": [path.relative_to(ROOT).as_posix() for path in source_files()],
        "source_set_sha256": set_digest,
        "entry_count": len(entries),
        "entries": entries,
    }


def render(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    expected = render(build_payload())
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != expected:
            print(f"source admission manifest is stale: {output}", file=sys.stderr)
            return 1
        print(f"source admission manifest valid: {output}")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(expected, encoding="utf-8")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
