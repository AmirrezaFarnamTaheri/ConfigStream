# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate that every browser-advertised download target exists in a release."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath

JS_TARGET_RE = re.compile(
    r"\b(?:file|dnsFile|dnsHardenedFile)\s*:\s*[\"'](?P<path>[^\"']+)[\"']"
)
HTML_TARGET_RE = re.compile(
    r"\b(?:data-file|data-dns-file|data-dns-hardened-file)=[\"'](?P<path>[^\"']+)[\"']"
)


def _safe_relative(value: str) -> str | None:
    if not value or "\\" in value or "\x00" in value:
        return None
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        return None
    return pure.as_posix()


def configured_targets(root: Path) -> set[str]:
    """Collect static artifact paths advertised by the release UI."""

    targets: set[str] = set()
    sources = (
        (root / "assets/js/dynamic-downloads.js", JS_TARGET_RE),
        (root / "index.html", HTML_TARGET_RE),
    )
    for path, pattern in sources:
        if not path.is_file():
            raise FileNotFoundError(f"missing frontend download catalog: {path.name}")
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            raw = match.group("path")
            safe = _safe_relative(raw)
            if safe is None:
                raise ValueError(f"unsafe frontend download target: {raw!r}")
            targets.add(safe)
    return targets


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    try:
        targets = configured_targets(root)
    except (OSError, UnicodeError, ValueError) as exc:
        return [str(exc)]

    manifest_paths: set[str] | None = None
    manifest_path = root / "artifact_manifest.json"
    if manifest_path.is_file():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            files = payload.get("files") if isinstance(payload, dict) else None
            if not isinstance(files, list):
                raise ValueError("artifact manifest files must be a list")
            manifest_paths = {
                str(item.get("path"))
                for item in files
                if isinstance(item, dict) and isinstance(item.get("path"), str)
            }
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"artifact manifest unreadable: {type(exc).__name__}: {exc}")

    for relative in sorted(targets):
        candidate = root.joinpath(*PurePosixPath(relative).parts)
        if not candidate.is_file() or candidate.is_symlink():
            errors.append(f"frontend download target is missing: {relative}")
            continue
        if manifest_paths is not None and relative not in manifest_paths:
            errors.append(f"frontend download target omitted from manifest: {relative}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", type=Path)
    args = parser.parse_args()
    errors = validate(args.artifact_dir)
    if errors:
        print("ERROR: frontend download target validation failed")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("OK: all browser-advertised download targets exist and are governed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
