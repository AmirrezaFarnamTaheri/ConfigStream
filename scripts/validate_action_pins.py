# SPDX-License-Identifier: AGPL-3.0-or-later
"""Enforce immutable references for every external GitHub Action.

GitHub documents a full-length commit SHA as the only immutable GitHub Action
reference.  Human-readable version comments are required beside each SHA so
reviewers can evaluate upgrades without giving up immutability.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

WORKFLOW_DIR = Path(".github") / "workflows"
PIN_MANIFEST = Path("config") / "github-action-pins.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
VERSION_COMMENT_RE = re.compile(r"(?:^|\s)(?P<version>v?\d+(?:\.\d+)*)(?:\s|$)")
USES_RE = re.compile(
    r"^\s*(?:-\s*)?uses:\s*(?P<uses>[^\s#]+)(?:\s+#\s*(?P<comment>.*))?$"
)


@dataclass(frozen=True)
class ActionPinAudit:
    errors: list[str]
    external_references: int
    sha_pinned: int
    container_digest_pinned: int


def _load_verified_pins(
    manifest_path: Path | None,
) -> tuple[dict[tuple[str, str], str], list[str]]:
    if manifest_path is None:
        return {}, []
    try:
        payload = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {}, [f"{manifest_path}: could not load verified action pins: {exc}"]
    if payload.get("schema_version") != 1 or not isinstance(payload.get("entries"), list):
        return {}, [f"{manifest_path}: unsupported verified action pin schema"]

    pins: dict[tuple[str, str], str] = {}
    errors: list[str] = []
    for index, item in enumerate(payload["entries"], start=1):
        if not isinstance(item, dict):
            errors.append(f"{manifest_path}: entry {index} must be an object")
            continue
        action = str(item.get("action", "")).strip()
        version = str(item.get("version", "")).strip()
        commit_sha = str(item.get("commit_sha", "")).strip()
        key = (action, version)
        if not action or not version or not SHA_RE.fullmatch(commit_sha):
            errors.append(f"{manifest_path}: entry {index} is incomplete or invalid")
            continue
        if key in pins:
            errors.append(f"{manifest_path}: duplicate verified pin for {action} {version}")
            continue
        pins[key] = commit_sha
    return pins, errors


def _validate_uses(
    *,
    path: Path,
    line_number: int,
    uses: str,
    comment: str | None,
    verified_pins: Mapping[tuple[str, str], str],
    require_verified_pin: bool,
) -> tuple[list[str], bool, bool]:
    if uses.startswith("./"):
        return [], False, False

    if uses.startswith("docker://"):
        image = uses.removeprefix("docker://")
        digest = image.rsplit("@", 1)[-1] if "@" in image else ""
        if DIGEST_RE.fullmatch(digest):
            return [], False, True
        return [
            f"{path}:{line_number}: container action '{uses}' must use an immutable sha256 digest"
        ], False, False

    if "@" not in uses:
        return [
            f"{path}:{line_number}: external action '{uses}' is missing an immutable full commit SHA"
        ], False, False

    name, ref = uses.rsplit("@", 1)
    if not SHA_RE.fullmatch(ref):
        return [
            f"{path}:{line_number}: external action '{uses}' must be pinned to a full commit SHA"
        ], False, False

    errors: list[str] = []
    version_match = VERSION_COMMENT_RE.search(comment or "")
    if version_match is None:
        errors.append(
            f"{path}:{line_number}: SHA-pinned action '{uses}' requires an inline version comment such as '# v4.2.0'"
        )
    elif require_verified_pin:
        version = version_match.group("version")
        expected = verified_pins.get((name, version))
        if expected is None:
            errors.append(
                f"{path}:{line_number}: action '{name}' version '{version}' is absent from the verified pin manifest"
            )
        elif ref != expected:
            errors.append(
                f"{path}:{line_number}: action '{name}' version '{version}' uses unverified SHA {ref}; expected {expected}"
            )
    return errors, True, False


def validate_action_pins(
    workflow_dir: Path = WORKFLOW_DIR,
    manifest_path: Path | None = PIN_MANIFEST,
) -> ActionPinAudit:
    verified_pins, errors = _load_verified_pins(manifest_path)
    require_verified_pin = manifest_path is not None and not errors
    external_references = 0
    sha_pinned = 0
    container_digest_pinned = 0
    observed_verified_pins: set[tuple[str, str]] = set()

    if not workflow_dir.exists():
        return ActionPinAudit(
            errors=[f"workflow directory not found: {workflow_dir}"],
            external_references=0,
            sha_pinned=0,
            container_digest_pinned=0,
        )

    workflow_files = sorted(
        path
        for pattern in ("*.yml", "*.yaml")
        for path in workflow_dir.glob(pattern)
    )
    if not workflow_files:
        return ActionPinAudit(
            errors=[f"no workflow files found in {workflow_dir}"],
            external_references=0,
            sha_pinned=0,
            container_digest_pinned=0,
        )

    for path in workflow_files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            errors.append(f"{path}: could not read workflow: {exc}")
            continue

        for line_number, line in enumerate(lines, start=1):
            match = USES_RE.match(line)
            if match is None:
                continue
            uses = match.group("uses")
            comment = match.group("comment")
            line_errors, is_sha, is_digest = _validate_uses(
                path=path,
                line_number=line_number,
                uses=uses,
                comment=comment,
                verified_pins=verified_pins,
                require_verified_pin=require_verified_pin,
            )
            if uses.startswith("./"):
                continue
            if uses.startswith("docker://") and is_digest:
                container_digest_pinned += 1
                continue
            external_references += 1
            sha_pinned += int(is_sha)
            errors.extend(line_errors)
            if require_verified_pin and "@" in uses:
                version_match = VERSION_COMMENT_RE.search(comment or "")
                if version_match is not None:
                    observed_verified_pins.add(
                        (uses.rsplit("@", 1)[0], version_match.group("version"))
                    )

    if require_verified_pin:
        for action, version in sorted(set(verified_pins) - observed_verified_pins):
            errors.append(
                f"{manifest_path}: verified pin is unused by workflows: {action} {version}"
            )

    return ActionPinAudit(
        errors=errors,
        external_references=external_references,
        sha_pinned=sha_pinned,
        container_digest_pinned=container_digest_pinned,
    )


def main() -> int:
    result = validate_action_pins()
    print("=== GitHub Actions Immutable Reference Audit ===")
    print(f"External GitHub Actions: {result.external_references}")
    print(f"Full-SHA pinned:         {result.sha_pinned}")
    print(f"Container digests:       {result.container_digest_pinned}")
    print()

    if result.errors:
        print("--- Errors ---")
        for error in result.errors:
            print(f"  - {error}")
        print("\nACTION PIN AUDIT FAILED")
        return 1

    print("ACTION PIN AUDIT PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
