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

ROOT = Path(__file__).resolve().parents[1]
PATTERN = r"(?i)(TODO|FIXME|XXX|MOCK|@mock|placeholder|assuming)"
OUT_MD = ROOT / "docs" / "DEBT_MATRIX.md"
OUT_JSON = ROOT / "docs" / "debt_matrix.json"


def _run_rg() -> list[dict[str, str | int]]:
    cmd = [
        "rg",
        "-n",
        "--json",
        "-S",
        PATTERN,
        str(ROOT),
    ]
    proc = subprocess.run(cmd, capture_output=True, check=False)
    if proc.returncode not in (0, 1):
        stderr = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or "rg failed")

    entries: list[dict[str, str | int]] = []
    stdout = (proc.stdout or b"").decode("utf-8", errors="replace")
    for line in stdout.splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "match":
            continue
        data = obj.get("data", {})
        path = data.get("path", {}).get("text", "")
        line_no = int(data.get("line_number", 0) or 0)
        text = (data.get("lines", {}).get("text", "") or "").rstrip()
        m = re.search(PATTERN, text, re.IGNORECASE)
        marker = m.group(1).upper() if m else "UNKNOWN"
        entries.append(
            {
                "path": path.replace("\\", "/"),
                "line": line_no,
                "marker": marker,
                "text": text.strip(),
            }
        )
    return entries


def _write_outputs(entries: list[dict[str, str | int]]) -> None:
    by_file: dict[str, list[dict[str, str | int]]] = defaultdict(list)
    marker_counts: dict[str, int] = defaultdict(int)
    for entry in entries:
        by_file[str(entry["path"])].append(entry)
        marker_counts[str(entry["marker"])] += 1

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
    md_lines.extend(
        [
            "",
            "## Triage Rules",
            "",
            "- `FIXME` / `XXX`: fix inline before release freeze.",
            "- `TODO`: create issue with owner + milestone.",
            "- `MOCK` / `@MOCK`: confirm test-only usage or replace.",
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
        json.dumps({"generated_at": timestamp, "entries": entries}, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    entries = _run_rg()
    _write_outputs(entries)
    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")
    print(f"Total markers: {len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
