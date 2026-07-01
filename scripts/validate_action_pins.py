# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate that GitHub Actions are pinned to a specific SHA for supply-chain security.

Best practice is to pin actions to a full commit SHA instead of a mutable version
tag (e.g., @v6). Version tags can be force-pushed, creating a supply-chain risk.
This script audits all workflow files and reports whether each action is SHA-pinned
or tag-pinned, so contributors can make informed pinning decisions.

See: https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions#using-third-party-actions
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

WORKFLOW_DIR = Path(".github") / "workflows"

# Actions that are known to be published by GitHub and are acceptable
# as version-tag references for CI convenience. These are first-party
# actions whose tags are signed and less likely to be compromised.
ALLOWED_TAG_ONLY_ACTIONS: set[str] = {
    "actions/",
    "gitleaks/gitleaks-action@",
}

# Actions that must be SHA-pinned due to their security sensitivity.
# This list can grow over time as we audit more actions.
REQUIRE_SHA_PIN_ACTIONS: set[str] = {
    "docker/login-action@",
    "docker/build-push-action@",
    "docker/setup-buildx-action@",
    "pypa/gh-action-pypi-publish@",
    "softprops/action-gh-release@",
    "actions/attest-build-provenance@",
}


def _is_sha_pinned(uses: str) -> bool:
    """Check if an action reference is pinned to a full commit SHA."""
    # SHA references are 40-character hex strings
    match = re.search(r"@([0-9a-f]{40})$", uses)
    return match is not None


def _is_tag_ref(uses: str) -> bool:
    """Check if an action reference uses a version tag (e.g., @v3, @v3.1.0)."""
    match = re.search(r"@v?\d+(\.\d+)*$", uses)
    return match is not None


def _is_branch_ref(uses: str) -> bool:
    """Check if an action reference uses a branch name."""
    # A ref that is not SHA and not a semver/docker tag
    match = re.search(r"@(main|master|latest|stable|develop|next)$", uses)
    return match is not None


def _is_docker_ref(uses: str) -> bool:
    """Check if an action reference is a Docker image (not a GitHub Action)."""
    return "docker://" in uses


def _action_name(uses: str) -> str:
    """Extract the action name from a uses line (without version)."""
    if "@" in uses:
        return uses.split("@")[0]
    return uses


def main() -> int:
    if not WORKFLOW_DIR.exists():
        print(f"ERROR: workflow directory not found: {WORKFLOW_DIR}")
        return 1

    workflow_files = sorted(
        path for pattern in ("*.yml", "*.yaml") for path in WORKFLOW_DIR.glob(pattern)
    )
    if not workflow_files:
        print(f"ERROR: no workflow files found in {WORKFLOW_DIR}")
        return 1

    all_actions: dict[str, list[dict[str, Any]]] = {}  # action_name -> [info]
    warnings: list[str] = []
    errors: list[str] = []

    for path in workflow_files:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            errors.append(f"{path}: could not read/parse: {exc}")
            continue

        if not isinstance(data, dict):
            continue

        jobs = data.get("jobs", {})
        if not isinstance(jobs, dict):
            continue

        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            steps = job.get("steps", [])
            if not isinstance(steps, list):
                continue

            for step_idx, step in enumerate(steps):
                if not isinstance(step, dict):
                    continue
                uses = step.get("uses")
                if not isinstance(uses, str):
                    continue

                # Skip local actions (./path/to/action) and Docker references
                if uses.startswith("./") or _is_docker_ref(uses):
                    continue

                name = _action_name(uses)
                pin_info = {
                    "file": str(path),
                    "job": job_name,
                    "step": step_idx,
                    "uses": uses,
                    "sha_pinned": _is_sha_pinned(uses),
                    "tag_pinned": _is_tag_ref(uses),
                    "branch_pinned": _is_branch_ref(uses),
                }

                if name not in all_actions:
                    all_actions[name] = []
                all_actions[name].append(pin_info)

                # Check if this action should be SHA-pinned
                requires_sha = any(
                    uses.startswith(req) for req in REQUIRE_SHA_PIN_ACTIONS
                )
                is_allowed_tag = any(
                    uses.startswith(allowed) for allowed in ALLOWED_TAG_ONLY_ACTIONS
                )

                if requires_sha and not pin_info["sha_pinned"]:
                    warnings.append(
                        f"{path}:{job_name}: action '{uses}' should be SHA-pinned "
                        f"(supply-chain sensitive action)"
                    )
                elif pin_info["branch_pinned"]:
                    warnings.append(
                        f"{path}:{job_name}: action '{uses}' is pinned to a mutable branch "
                        f"— pin to a version tag or SHA instead"
                    )
                elif not pin_info["sha_pinned"] and not is_allowed_tag:
                    if pin_info["tag_pinned"]:
                        warnings.append(
                            f"{path}:{job_name}: action '{uses}' uses a mutable version tag "
                            f"— consider pinning to a full commit SHA for supply-chain security"
                        )
                    else:
                        warnings.append(
                            f"{path}:{job_name}: action '{uses}' uses an atypical reference "
                            f"(not SHA, semver tag, or known prefix)"
                        )

    # Print summary
    print("=== GitHub Actions Version Pinning Audit ===")
    print()

    sha_count = sum(
        1 for infos in all_actions.values() for info in infos if info["sha_pinned"]
    )
    tag_count = sum(
        1 for infos in all_actions.values() for info in infos
        if not info["sha_pinned"] and info["tag_pinned"]
    )
    branch_count = sum(
        1 for infos in all_actions.values() for info in infos
        if info["branch_pinned"]
    )
    total = sha_count + tag_count + branch_count

    print(f"Total actions referenced: {total}")
    print(f"  ✅ SHA-pinned:           {sha_count}")
    print(f"  ⚠️  Tag-pinned:           {tag_count}")
    print(f"  ❌ Branch-pinned:        {branch_count}")
    print()

    # Detailed per-action breakdown
    print("--- Per-Action Detail ---")
    for name in sorted(all_actions.keys()):
        infos = all_actions[name]
        refs = [info["uses"] for info in infos]
        unique_refs = sorted(set(refs))
        files = sorted(set(info["file"] for info in infos))
        print(f"\n  {name}")
        for ref in unique_refs:
            sha = _is_sha_pinned(ref)
            tag = _is_tag_ref(ref)
            branch = _is_branch_ref(ref)
            status = "✅ SHA" if sha else ("❌ Branch" if branch else "⚠️  Tag")
            print(f"    {status}  {ref}")
        print(f"    Files: {', '.join(files)}")

    print()
    if warnings:
        print("--- Warnings ---")
        for w in warnings:
            print(f"  ⚠️  {w}")
        print()

    if errors:
        print("--- Errors ---")
        for e in errors:
            print(f"  ❌ {e}")
        print()
        print("ACTION PIN AUDIT FAILED")
        return 1

    print("ACTION PIN AUDIT PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
