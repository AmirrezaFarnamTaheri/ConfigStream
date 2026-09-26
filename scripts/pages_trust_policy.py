# SPDX-License-Identifier: AGPL-3.0-or-later
"""Resolve the explicit unsigned GitHub Pages publication policy."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = REPO_ROOT / "config" / "pages-trust-policy.json"


def resolve_allow_unsigned_pages(
    *,
    repository: str,
    override: str | None,
    policy_path: Path = DEFAULT_POLICY_PATH,
    signing_configured: bool = True,
) -> bool:
    """Resolve an override against the repository-bound committed policy.

    ``signing_configured`` reports whether a usable signing keypair exists for
    this run. When it does not, unsigned publication is permitted regardless of
    the committed default: an absent or broken optional secret must degrade the
    trust level, never stop the project from publishing.
    """

    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Pages trust policy is unreadable: {exc}") from exc
    if not isinstance(policy, dict):
        raise ValueError("Pages trust policy must be a JSON object")
    if policy.get("schema_version") != 1:
        raise ValueError("unsupported Pages trust policy schema")

    bound_repository = policy.get("repository")
    if not isinstance(bound_repository, str) or not bound_repository.strip():
        raise ValueError("Pages trust policy repository binding is invalid")
    committed_allow = policy.get("allow_unsigned_pages")
    if not isinstance(committed_allow, bool):
        raise ValueError("Pages trust policy allow_unsigned_pages must be boolean")
    if not repository or not repository.strip():
        raise ValueError("GitHub repository identity is required")

    raw_override = (override or "").strip().lower()
    if raw_override not in {"", "true", "false"}:
        raise ValueError("ALLOW_UNSIGNED_PAGES must be true, false, or unset")
    if raw_override:
        return raw_override == "true"
    if not signing_configured:
        return True
    return bound_repository == repository and committed_allow


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY_PATH)
    args = parser.parse_args()
    try:
        raw_signing = (os.environ.get("SIGNING_CONFIGURED") or "true").strip().lower()
        if raw_signing not in {"true", "false"}:
            raise ValueError("SIGNING_CONFIGURED must be true, false, or unset")
        allowed = resolve_allow_unsigned_pages(
            repository=os.environ.get("REPOSITORY", ""),
            override=os.environ.get("VARIABLE_ALLOW_UNSIGNED_PAGES"),
            policy_path=args.policy,
            signing_configured=raw_signing == "true",
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print("true" if allowed else "false")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
