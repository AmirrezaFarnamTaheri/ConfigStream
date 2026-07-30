# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate that Bandit suppressions are narrow, real comments, and auditable."""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess  # nosec B404
import sys
import tempfile
import tokenize
from pathlib import Path
from typing import Any

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
        elif root.exists():
            files.extend(
                path
                for path in root.rglob("*")
                if path.is_file() and path.suffix in SOURCE_SUFFIXES
            )
    return sorted(set(files))


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


def _python_comments(source: str) -> dict[int, str]:
    comments: dict[int, str] = {}
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for token in tokens:
            if token.type == tokenize.COMMENT:
                comments[token.start[0]] = token.string
    except (IndentationError, SyntaxError, tokenize.TokenError):
        return {}
    return comments


def _nosec_comments(path: Path, source: str) -> list[tuple[int, re.Match[str]]]:
    if path.suffix == ".py":
        lines = _python_comments(source)
        return [
            (line_no, match)
            for line_no, comment in lines.items()
            if (match := NOSEC_RE.search(comment)) is not None
        ]
    return [
        (line_no, match)
        for line_no, line in enumerate(source.splitlines(), 1)
        if (match := NOSEC_RE.search(line)) is not None
    ]


def _diagnostic_excerpt(completed: subprocess.CompletedProcess[str]) -> str:
    diagnostic = "\n".join(
        value.strip()
        for value in (completed.stderr, completed.stdout)
        if value and value.strip()
    )
    return diagnostic[:2000] if diagnostic else "no diagnostic output"


def _load_bandit_report(
    report_path: Path, completed: subprocess.CompletedProcess[str]
) -> dict[str, Any]:
    try:
        content = report_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(
            "Bandit report could not be read: "
            f"{exc}; diagnostic: {_diagnostic_excerpt(completed)}"
        ) from exc
    if not content:
        raise RuntimeError(
            "Bandit produced an empty JSON report; diagnostic: "
            f"{_diagnostic_excerpt(completed)}"
        )
    try:
        report: object = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Bandit returned invalid JSON: "
            f"{exc}; diagnostic: {_diagnostic_excerpt(completed)}"
        ) from exc
    if not isinstance(report, dict):
        raise RuntimeError("Bandit JSON report root must be an object")
    results = report.get("results")
    if not isinstance(results, list):
        raise RuntimeError("Bandit JSON report must contain a results list")
    return report


def _collect_active_bandit_findings(scan_roots: tuple[str, ...]) -> FindingMap:
    python_roots = tuple(root for root in scan_roots if (ROOT / root).suffix != ".js")
    if not python_roots:
        return {}
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
        report_path = Path(handle.name)
    command = [
        sys.executable,
        "-m",
        "bandit",
        "-r",
        *python_roots,
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
                f"{completed.returncode}: {_diagnostic_excerpt(completed)}"
            )
        report = _load_bandit_report(report_path, completed)
    finally:
        report_path.unlink(missing_ok=True)
    findings: FindingMap = {}
    for result in report["results"]:
        if not isinstance(result, dict):
            raise RuntimeError("Bandit results must contain only objects")
        filename = _repo_relative(str(result.get("filename", "")))
        line_number = int(result.get("line_number", 0) or 0)
        test_id = str(result.get("test_id", "")).strip()
        if filename and line_number > 0 and RULE_RE.fullmatch(test_id):
            findings.setdefault((filename, line_number), set()).add(test_id)
    return findings


def _inert_exception_suppression(path: Path, line_no: int, token: str) -> bool:
    if path.suffix != ".py" or token not in {"B110", "B112"}:
        return False
    lines = path.read_text(encoding="utf-8").splitlines()
    window = "\n".join(lines[max(0, line_no - 1) : min(len(lines), line_no + 7)])
    return any(marker in window for marker in ("logger.", "logging.", "raise", "print("))


def validate_bandit_suppressions(
    scan_roots: tuple[str, ...] = DEFAULT_SCAN_ROOTS,
    active_findings: FindingMap | None = None,
) -> list[str]:
    errors: list[str] = []
    for path in _iter_source_files(scan_roots):
        rel_path = str(path.relative_to(ROOT))
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"{rel_path}: cannot decode as UTF-8: {exc}")
            continue
        for line_no, match in _nosec_comments(path, source):
            tokens = _rule_tokens(match.group("body"))
            if not tokens:
                errors.append(
                    f"{rel_path}:{line_no}: bare Bandit suppression is forbidden; "
                    "pin exact rule IDs"
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
            if active_findings is None:
                continue
            active_tokens = active_findings.get((rel_path, line_no), set())
            stale_tokens = [
                token
                for token in tokens
                if RULE_RE.fullmatch(token)
                and token not in active_tokens
                and not _inert_exception_suppression(path, line_no, token)
            ]
            if stale_tokens:
                errors.append(
                    f"{rel_path}:{line_no}: stale or misplaced nosec rule token(s): "
                    f"{', '.join(stale_tokens)}"
                )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--require-active", action="store_true")
    args = parser.parse_args(argv)
    scan_roots = tuple(args.paths) if args.paths else DEFAULT_SCAN_ROOTS
    active_findings = (
        _collect_active_bandit_findings(scan_roots) if args.require_active else None
    )
    errors = validate_bandit_suppressions(scan_roots, active_findings)
    if errors:
        print("\n".join(errors))
        return 1
    suffix = " and audited active/inert findings" if args.require_active else ""
    print(f"OK: Bandit suppressions are pinned to explicit rule IDs{suffix}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
