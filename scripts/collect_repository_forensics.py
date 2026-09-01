# SPDX-License-Identifier: AGPL-3.0-or-later
"""Record what repository-forensics claims can and cannot be proven from this snapshot."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import TypedDict, cast

SOURCE_METADATA = Path("config/source-snapshot.json")
OUTPUT_JSON = Path("docs/generated/repository-forensics.json")
OUTPUT_MD = Path("docs/generated/repository-forensics.md")
_PATTERNS = {
    "private-key-block": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    ),
    "github-token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "slack-token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
}
_EXCLUDED = {
    ".git",
    ".venv",
    "node_modules",
    "frontend-dist",
    "output",
    "data",
    "__pycache__",
}


class SourceSnapshot(TypedDict):
    archive_sha256: str
    archive_entry_count: int


class SecretFinding(TypedDict):
    path: str
    kind: str
    match_count: int


class SecretScan(TypedDict):
    status: str
    finding_count: int
    findings: list[SecretFinding]
    limitations: str


class ForensicsReport(TypedDict):
    schema_version: int
    source: SourceSnapshot
    remediation_checkout: dict[str, str | bool]
    current_tree_secret_scan: SecretScan
    unavailable_claims: dict[str, str]


def _current_tree_findings(root: Path) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    for directory, dirnames, filenames in os.walk(
        root, topdown=True, onerror=lambda _error: None, followlinks=False
    ):
        dirnames[:] = sorted(name for name in dirnames if name not in _EXCLUDED)
        for filename in sorted(filenames):
            path = Path(directory) / filename
            try:
                if path.stat().st_size > 2_000_000:
                    continue
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for kind, pattern in _PATTERNS.items():
                matches = list(pattern.finditer(text))
                if matches:
                    findings.append(
                        {
                            "path": path.relative_to(root).as_posix(),
                            "kind": kind,
                            "match_count": len(matches),
                        }
                    )
    return findings


def build(root: Path) -> ForensicsReport:
    source = cast(
        SourceSnapshot,
        json.loads((root / SOURCE_METADATA).read_text(encoding="utf-8")),
    )
    current_findings = _current_tree_findings(root)
    return {
        "schema_version": 1,
        "source": source,
        "remediation_checkout": {
            "history_origin": "local baseline created from the archive for remediation; not upstream history",
            "upstream_history_available": False,
        },
        "current_tree_secret_scan": {
            "status": "complete-high-signal-regex",
            "finding_count": len(current_findings),
            "findings": current_findings,
            "limitations": "Pattern scan only; findings include locations and categories, never secret values.",
        },
        "unavailable_claims": {
            "upstream_commit_history": "not present in the supplied archive",
            "deleted_secrets_history": "requires a full upstream Git clone and history scanner",
            "code_ownership": "requires original authorship history",
            "branch_protection": "requires authenticated GitHub repository metadata",
            "github_project_state": "requires trusted ProjectV2 binding and authenticated metadata",
            "remote_ci_head": "requires a pushed commit and exact-head GitHub Actions results",
        },
    }


def _markdown(payload: ForensicsReport) -> str:
    source = payload["source"]
    scan = payload["current_tree_secret_scan"]
    lines = [
        "# Repository forensics evidence",
        "",
        "This checkout came from an archive snapshot. The local Git commit is a remediation rollback point, not upstream history.",
        "",
        f"Source archive SHA-256: `{source['archive_sha256']}`",
        f"Archive entries: **{source['archive_entry_count']}**",
        f"Current-tree high-signal findings: **{scan['finding_count']}**",
        "",
        "## Current-tree scan",
        "",
    ]
    if scan["findings"]:
        lines.extend(["| Path | Category | Matches |", "|---|---|---:|"])
        for item in scan["findings"]:
            lines.append(
                f"| `{item['path']}` | {item['kind']} | {item['match_count']} |"
            )
    else:
        lines.append("No high-signal current-tree secret pattern was found.")
    lines.extend(["", "## Evidence unavailable from the archive", ""])
    for name, reason in payload["unavailable_claims"].items():
        lines.append(f"- **{name.replace('_', ' ')}:** {reason}")
    return "\n".join(lines) + "\n"


def generate(root: Path, *, check: bool = False) -> list[str]:
    root = Path(root)
    payload = build(root)
    targets = {
        root / OUTPUT_JSON: json.dumps(payload, indent=2, sort_keys=True) + "\n",
        root / OUTPUT_MD: _markdown(payload),
    }
    errors: list[str] = []
    for path, content in targets.items():
        if check:
            try:
                current = path.read_text(encoding="utf-8")
            except OSError:
                errors.append(
                    f"missing repository forensics evidence: {path.relative_to(root)}"
                )
                continue
            if current != content:
                errors.append(
                    f"repository forensics evidence is stale: {path.relative_to(root)}"
                )
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if payload["current_tree_secret_scan"]["finding_count"]:
        errors.append("high-signal current-tree secret patterns require review")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    errors = generate(Path("."), check=args.check)
    if errors:
        print("ERROR: repository forensics evidence has findings or drift")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(
        "OK: current-tree forensics is clean; upstream-history limitations are explicit"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
