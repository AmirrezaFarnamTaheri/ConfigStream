# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate tracked static assets and intentional zero-byte markers."""

from __future__ import annotations

import re
import shutil
import subprocess  # nosec B404
import sys
from types import ModuleType
from pathlib import Path

from configstream.security_validator import SecurityValidator

ENCODING = "utf-8"
ROOT = Path(__file__).resolve().parents[1]

ALLOWED_ZERO_BYTE_FILES = {
    ".nojekyll",
    "src/configstream/py.typed",
}

TEXT_REF_EXTENSIONS = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}

IMAGE_EXTENSIONS = {
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".png",
    ".svg",
    ".webp",
}

SKIP_REF_PREFIXES = (
    "#",
    "data:",
    "http://",
    "https://",
    "mailto:",
    "tel:",
)

TEMPLATE_MARKERS = ("${", "{{", "<%")

EXCLUDED_REFERENCE_ROOTS = {
    ".git",
    ".hypothesis",
    ".pytest_cache",
    "docs/DEBT_MATRIX.md",
    "docs/debt_matrix.json",
    "node_modules",
}

ASSET_REF_RE = re.compile(
    r"""(?P<quote>['"])(?P<ref>(?:\.\.?/|assets/|frontend/assets/)[^'"]+\.(?:gif|ico|jpe?g|png|svg|webp)(?:[?#][^'"]*)?)(?P=quote)""",
    re.IGNORECASE,
)


def _resolve_svg_parser() -> tuple[ModuleType, tuple[type[BaseException], ...]]:
    """Return an XML parser for tracked SVG validation without hard failing on extras."""

    try:
        from defusedxml import ElementTree as safe_et
        from defusedxml.common import DefusedXmlException

        parse_errors: tuple[type[BaseException], ...] = (
            DefusedXmlException,
            safe_et.ParseError,
            SyntaxError,
            UnicodeDecodeError,
            OSError,
        )
        return safe_et, parse_errors
    except ModuleNotFoundError:
        # The secure parser is preferred; this compatibility fallback is only
        # reachable in environments that do not install the optional validator.
        import xml.etree.ElementTree as safe_et  # nosec B405

        parse_errors = (
            safe_et.ParseError,
            SyntaxError,
            UnicodeDecodeError,
            OSError,
        )
        return safe_et, parse_errors


def _repo_relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _tracked_files() -> list[Path]:
    git_bin = shutil.which("git")
    if not git_bin:
        return sorted(
            path
            for path in ROOT.rglob("*")
            if path.is_file() and ".git" not in path.relative_to(ROOT).parts
        )
    try:
        completed = subprocess.run(  # nosec B603
            [git_bin, "ls-files", "-z"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return sorted(
            path
            for path in ROOT.rglob("*")
            if path.is_file() and ".git" not in path.relative_to(ROOT).parts
        )

    names = [name.decode(ENCODING) for name in completed.stdout.split(b"\0") if name]
    return [ROOT / name for name in names if (ROOT / name).is_file()]


def _is_excluded_reference(path: Path) -> bool:
    rel = _repo_relative(path)
    parts = set(Path(rel).parts)
    return any(
        rel == excluded or excluded in parts for excluded in EXCLUDED_REFERENCE_ROOTS
    )


def _strip_suffixes(ref: str) -> str:
    return ref.split("#", 1)[0].split("?", 1)[0]


def _resolve_asset_ref(source: Path, ref: str) -> Path | None:
    clean_ref = _strip_suffixes(ref).replace("\\", "/")
    lowered = clean_ref.lower()
    if lowered.startswith(SKIP_REF_PREFIXES) or any(
        marker in clean_ref for marker in TEMPLATE_MARKERS
    ):
        return None
    if clean_ref.startswith("frontend/assets/"):
        return ROOT / clean_ref
    if clean_ref.startswith("assets/"):
        return ROOT / "frontend" / clean_ref
    return (source.parent / clean_ref).resolve()


def _validate_zero_byte_files(tracked: list[Path]) -> list[str]:
    errors: list[str] = []
    for path in tracked:
        rel = _repo_relative(path)
        if path.stat().st_size == 0 and rel not in ALLOWED_ZERO_BYTE_FILES:
            errors.append(f"tracked zero-byte file is not allowlisted: {rel}")
    return errors


def _validate_image_references(tracked: list[Path]) -> list[str]:
    errors: list[str] = []
    for path in tracked:
        if path.suffix.lower() not in TEXT_REF_EXTENSIONS:
            continue
        if _is_excluded_reference(path):
            continue
        try:
            text = path.read_text(encoding=ENCODING)
        except UnicodeDecodeError:
            continue
        for match in ASSET_REF_RE.finditer(text):
            ref = match.group("ref")
            target = _resolve_asset_ref(path, ref)
            if target is None:
                continue
            try:
                rel_target = _repo_relative(target)
            except ValueError:
                errors.append(
                    f"{_repo_relative(path)} references image outside repo: {ref}"
                )
                continue
            if not target.exists():
                errors.append(f"{_repo_relative(path)} references missing image: {ref}")
                continue
            if target.suffix.lower() in IMAGE_EXTENSIONS and target.stat().st_size == 0:
                errors.append(
                    f"{_repo_relative(path)} references empty image: {rel_target}"
                )
    return errors


def _validate_svg_xml(tracked: list[Path]) -> list[str]:
    safe_et, parse_errors = _resolve_svg_parser()
    errors: list[str] = []
    for path in tracked:
        if path.suffix.lower() != ".svg":
            continue
        try:
            safe_et.parse(path)  # nosec B314
        except parse_errors as exc:
            diagnostic = SecurityValidator.sanitize_log_message(
                " ".join(str(exc).split())
            )
            errors.append(f"malformed SVG XML in {_repo_relative(path)}: {diagnostic}")
    return errors


def validate_assets() -> list[str]:
    tracked = _tracked_files()
    return (
        _validate_zero_byte_files(tracked)
        + _validate_image_references(tracked)
        + _validate_svg_xml(tracked)
    )


def main() -> None:
    errors = validate_assets()
    if errors:
        print("ERROR: asset validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print("OK: tracked assets validated.")


if __name__ == "__main__":
    main()
