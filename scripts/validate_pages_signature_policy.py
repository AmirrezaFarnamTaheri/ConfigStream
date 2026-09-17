# SPDX-License-Identifier: AGPL-3.0-or-later
"""Enforce the production Pages signing and source-freshness policy."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_pages_artifact import (
    _public_key_hex_from_env,
    _validate_manifest_signature,
)

_TRUTHY = {"1", "true", "yes"}


def _allow_unsigned_pages() -> bool:
    return os.environ.get("ALLOW_UNSIGNED_PAGES", "").strip().lower() in _TRUTHY


def _validate_current_main_source() -> list[str]:
    """Fail closed when a deploy candidate no longer represents current main.

    ``EXPECTED_SOURCE_SHA`` is set by the Pages deployment workflow after it
    authenticates the source Config's Stream run. Normal offline/unit use does
    not set it, so signature validation remains usable outside GitHub Actions.
    """

    expected = (os.environ.get("EXPECTED_SOURCE_SHA") or "").strip().lower()
    if not expected:
        return []
    if len(expected) != 40 or any(char not in "0123456789abcdef" for char in expected):
        return ["EXPECTED_SOURCE_SHA is not a valid Git commit SHA"]

    repository = (os.environ.get("GITHUB_REPOSITORY") or "").strip()
    if not repository or repository.count("/") != 1:
        return [
            "EXPECTED_SOURCE_SHA is set but GITHUB_REPOSITORY is unavailable; "
            "cannot verify deployment freshness"
        ]

    api_url = (os.environ.get("GITHUB_API_URL") or "https://api.github.com").rstrip("/")
    request = Request(
        f"{api_url}/repos/{repository}/branches/main",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "ConfigStream-Pages"},
    )
    token = (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip()
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    try:
        with urlopen(request, timeout=10) as response:  # nosec B310 - fixed GitHub API origin
            payload = json.load(response)
    except (HTTPError, URLError, OSError, json.JSONDecodeError, TimeoutError) as exc:
        return [f"could not verify current main revision: {type(exc).__name__}"]

    try:
        current = str(payload["commit"]["sha"]).strip().lower()
    except (KeyError, TypeError, AttributeError):
        return ["GitHub main-branch response did not contain a commit SHA"]

    if current != expected:
        return [
            "deployment source is stale: "
            f"source={expected}, current_main={current}; refusing Pages publication"
        ]
    return []


def validate_pages_signature_policy(root: Path) -> list[str]:
    root = Path(root)
    manifest_path = root / "artifact_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        return [f"could not read artifact_manifest.json: {exc}"]
    except json.JSONDecodeError as exc:
        return [f"invalid artifact_manifest.json: {exc}"]
    if not isinstance(manifest, dict):
        return ["artifact_manifest.json must be a JSON object"]

    freshness_errors = _validate_current_main_source()
    if freshness_errors:
        return freshness_errors

    raw_public_key = (os.environ.get("CS_PUBLIC_KEY") or "").strip()
    public_key_hex = _public_key_hex_from_env()
    signature = manifest.get("manifest_signature")

    if raw_public_key and not public_key_hex:
        return ["CS_PUBLIC_KEY is configured but is not a valid Ed25519 public key"]

    if public_key_hex:
        return _validate_manifest_signature(manifest)

    if signature is not None:
        return [
            "artifact_manifest.json is signed but CS_PUBLIC_KEY is not configured; "
            "signed artifacts must never be accepted without a trust anchor"
        ]

    if not _allow_unsigned_pages():
        return [
            "unsigned Pages publication is disabled by default; configure signing "
            "or explicitly set repository variable ALLOW_UNSIGNED_PAGES=true"
        ]

    return []


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output")
    errors = validate_pages_signature_policy(root)
    if errors:
        print("ERROR: Pages signature policy rejected the artifact", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    mode = "signed" if _public_key_hex_from_env() else "explicit-unsigned"
    print(f"OK: Pages signature policy accepted artifact in {mode} mode")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
