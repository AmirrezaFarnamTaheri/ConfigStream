# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate that Bandit suppressions are narrow and auditable."""

from __future__ import annotations

import argparse
import json
import re
import subprocess  # nosec B404
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCAN_ROOTS = (
    "src/configstream",
    "scripts",
    "tools",
    "frontend/assets/js",
)
SOURCE_SUFFIXES = {".py", ".js"}
NOSEC_RE = re.compile(r"#\s*nosec(?P<body>[^\r\n]*)")
RULE_RE = re.compile(r"^B\d{3}$")
FindingMap = dict[tuple[str, int], set[str]]


def _iter_source_files(scan_roots: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for rel_root in scan_roots:
        root = ROOT / rel_root
        if root.is_file() and root.suffix in SOURCE_SUFFIXES:
            files.append(root)
            continue
        if not root.exists():
            continue
        files.extend(
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix in SOURCE_SUFFIXES
        )
    return sorted(files)


def _rule_tokens(body: str) -> list[str]:
    return [token.strip() for token in body.replace(",", " ").split() if token.strip()]


def _repo_relative(path_value: str | Path) -> str:
    path = Path(path_value)
    try:
        if path.is_absolute():
            return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        pass
    return str(path)


def _collect_active_bandit_findings(scan_roots: tuple[str, ...]) -> FindingMap:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
        report_path = Path(handle.name)

    command = [
        sys.executable,
        "-m",
        "bandit",
        "-r",
        *scan_roots,
        "-q",
        "--ignore-nosec",
        "-f",
        "json",
        "-o",
        str(report_path),
    ]
    try:
        completed = subprocess.run(  # nosec B603
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode not in {0, 1}:
            raise RuntimeError(
                "Bandit active-finding scan failed with exit code "
                f"{completed.returncode}: {completed.stderr.strip()}"
            )
        report = json.loads(report_path.read_text(encoding="utf-8"))
    finally:
        report_path.unlink(missing_ok=True)

    findings: FindingMap = {}
    for result in report.get("results", []):
        filename = _repo_relative(str(result.get("filename", "")))
        line_number = int(result.get("line_number", 0) or 0)
        test_id = str(result.get("test_id", "")).strip()
        if filename and line_number > 0 and RULE_RE.fullmatch(test_id):
            findings.setdefault((filename, line_number), set()).add(test_id)
    return findings


def validate_bandit_suppressions(
    scan_roots: tuple[str, ...] = DEFAULT_SCAN_ROOTS,
    active_findings: FindingMap | None = None,
) -> list[str]:
    errors: list[str] = []
    for path in _iter_source_files(scan_roots):
        rel_path = str(path.relative_to(ROOT))
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError as exc:
            errors.append(f"{rel_path}: cannot decode as UTF-8: {exc}")
            continue

        for line_no, line in enumerate(lines, 1):
            match = NOSEC_RE.search(line)
            if not match:
                continue

            tokens = _rule_tokens(match.group("body"))
            if not tokens:
                errors.append(
                    f"{rel_path}:{line_no}: bare Bandit suppression is forbidden; "
                    "pin exact rule IDs such as '# no' + 'sec B603'"
                )
                continue

            invalid = [token for token in tokens if not RULE_RE.fullmatch(token)]
            if invalid:
                errors.append(
                    f"{rel_path}:{line_no}: invalid nosec rule token(s): "
                    f"{', '.join(invalid)}"
                )

            duplicates = sorted({token for token in tokens if tokens.count(token) > 1})
            if duplicates:
                errors.append(
                    f"{rel_path}:{line_no}: duplicate nosec rule token(s): "
                    f"{', '.join(duplicates)}"
                )

            if active_findings is not None:
                active_tokens = active_findings.get((rel_path, line_no), set())
                stale_tokens = [
                    token
                    for token in tokens
                    if RULE_RE.fullmatch(token) and token not in active_tokens
                ]
                if stale_tokens:
                    errors.append(
                        f"{rel_path}:{line_no}: stale or misplaced nosec rule "
                        f"token(s): {', '.join(stale_tokens)}"
                    )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional repository-relative files or directories to scan.",
    )
    parser.add_argument(
        "--require-active",
        action="store_true",
        help=(
            "Also run Bandit with --ignore-nosec and require every pinned "
            "suppression to match an active finding on the same line."
        ),
    )
    args = parser.parse_args(argv)

    scan_roots = tuple(args.paths) if args.paths else DEFAULT_SCAN_ROOTS
    active_findings = (
        _collect_active_bandit_findings(scan_roots) if args.require_active else None
    )
    errors = validate_bandit_suppressions(scan_roots, active_findings)
    if errors:
        for error in errors:
            print(error)
        return 1

    suffix = " and active Bandit findings" if args.require_active else ""
    print(f"OK: Bandit suppressions are pinned to explicit rule IDs{suffix}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
