#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generate a repository debt matrix from TODO/FIXME-style markers."""

from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
PATTERN = r"(?i)(TODO|FIXME|XXX|MOCK|@mock|placeholder|assuming)"
OUT_MD = ROOT / "docs" / "DEBT_MATRIX.md"
OUT_JSON = ROOT / "docs" / "debt_matrix.json"
GENERATED_PATHS = {
    "docs/DEBT_MATRIX.md",
    "docs/debt_matrix.json",
}
EXCLUDED_PREFIXES = (
    ".git/",
    ".pytest_cache/",
    ".mypy_cache/",
    "__pycache__/",
    "docs/encyclopedia/",
    "frontend/assets/fonts/vendor/",
    "frontend/assets/images/flags/",
    "frontend/assets/libs/",
    "node_modules/",
)
TEXT_SUFFIXES = {
    ".cfg",
    ".cjs",
    ".css",
    ".go",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


def _repo_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _is_scannable(rel_path: str) -> bool:
    if rel_path in GENERATED_PATHS:
        return False
    if any(rel_path.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return False
    return Path(rel_path).suffix.lower() in TEXT_SUFFIXES


def _tracked_files() -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return [
            ROOT / line.strip()
            for line in proc.stdout.splitlines()
            if line.strip() and _is_scannable(line.strip().replace("\\", "/"))
        ]
    return [
        path
        for path in ROOT.rglob("*")
        if path.is_file() and _is_scannable(_repo_path(path))
    ]


def _classify_path(rel_path: str) -> str:
    if rel_path.startswith("tests/"):
        return "test"
    if "/test_" in rel_path or rel_path.endswith("_test.go"):
        return "test"
    if rel_path.startswith("scripts/"):
        return "tooling"
    if rel_path.startswith(".github/"):
        return "ci"
    if rel_path.startswith("docs/") or rel_path in {"README.md", "STATUS.md", "CHANGELOG.md"}:
        return "docs"
    if rel_path.startswith("frontend/"):
        return "frontend"
    if rel_path.startswith("src/"):
        return "production"
    return "other"


def _scan_files(paths: Iterable[Path]) -> list[dict[str, str | int]]:
    marker_re = re.compile(PATTERN, re.IGNORECASE)

    entries: list[dict[str, str | int]] = []
    for path in paths:
        rel_path = _repo_path(path)
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_no, text in enumerate(lines, start=1):
            match = marker_re.search(text)
            if not match:
                continue
            marker = match.group(1).upper().lstrip("@")
            entries.append(
                {
                    "path": rel_path,
                    "line": line_no,
                    "marker": marker,
                    "category": _classify_path(rel_path),
                    "text": text.strip(),
                }
            )
    return entries


def _write_outputs(entries: list[dict[str, str | int]]) -> None:
    by_file: dict[str, list[dict[str, str | int]]] = defaultdict(list)
    marker_counts: dict[str, int] = defaultdict(int)
    category_counts: dict[str, int] = defaultdict(int)
    for entry in entries:
        by_file[str(entry["path"])].append(entry)
        marker_counts[str(entry["marker"])] += 1
        category_counts[str(entry["category"])] += 1

    timestamp = datetime.now(timezone.utc).isoformat()
    md_lines = [
        "# Debt Matrix",
        "",
        f"Generated: `{timestamp}`",
        "",
        "## Summary",
        "",
        f"- Total markers: **{len(entries)}**",
    ]
    for marker in sorted(marker_counts):
        md_lines.append(f"- `{marker}`: **{marker_counts[marker]}**")
    md_lines.extend(["", "## Categories", ""])
    for category in sorted(category_counts):
        md_lines.append(f"- `{category}`: **{category_counts[category]}**")
    md_lines.extend(
        [
            "",
            "## Triage Rules",
            "",
            "- `FIXME` / `XXX`: fix inline before release freeze.",
            "- `TODO`: create issue with owner + milestone.",
            "- `MOCK` / `@MOCK`: production mocks require owner review; test-only mocks are tracked separately.",
            "- `PLACEHOLDER` / `ASSUMING`: remove assumptions, enforce validation.",
            "",
            "## Findings",
            "",
            "| File | Marker Count | Markers |",
            "| --- | ---: | --- |",
        ]
    )

    for path in sorted(by_file):
        markers = sorted({str(e["marker"]) for e in by_file[path]})
        md_lines.append(f"| `{path}` | {len(by_file[path])} | {', '.join(markers)} |")

    md_lines.extend(["", "## Raw Entries", ""])
    for path in sorted(by_file):
        md_lines.append(f"### `{path}`")
        for entry in sorted(by_file[path], key=lambda x: int(x["line"])):
            md_lines.append(
                f"- L{entry['line']} [`{entry['marker']}`] `{entry['text']}`"
            )
        md_lines.append("")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(md_lines).rstrip() + "\n", encoding="utf-8")

    OUT_JSON.write_text(
        json.dumps(
            {
                "generated_at": timestamp,
                "summary": {
                    "total": len(entries),
                    "markers": dict(sorted(marker_counts.items())),
                    "categories": dict(sorted(category_counts.items())),
                },
                "entries": entries,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> int:
    entries = _scan_files(_tracked_files())
    _write_outputs(entries)
    print(f"Wrote {OUT_MD.relative_to(ROOT)}")
    print(f"Wrote {OUT_JSON.relative_to(ROOT)}")
    print(f"Total markers: {len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
