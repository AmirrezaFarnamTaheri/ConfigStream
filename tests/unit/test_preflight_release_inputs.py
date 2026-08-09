# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from scripts.preflight_release_inputs import validate_release_inputs
from scripts.validate_frontend_placeholders import _resolve_public_key

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "preflight_release_inputs.py"


def test_preflight_accepts_public_key_derived_from_signing_key() -> None:
    assert validate_release_inputs({"CS_SIGNING_PRIVATE_KEY_HEX": "01" * 32}) == []


def test_preflight_rejects_missing_release_trust_anchor() -> None:
    errors = validate_release_inputs({})
    assert any("verification key is unavailable" in error for error in errors)


def test_preflight_rejects_malformed_explicit_public_key() -> None:
    errors = validate_release_inputs({"CS_PUBLIC_KEY": "not-an-ed25519-key"})
    assert any("not a valid Ed25519 public key" in error for error in errors)


def test_preflight_rejects_public_key_that_does_not_match_signing_key() -> None:
    unrelated_public_key = _resolve_public_key(
        {"CS_SIGNING_PRIVATE_KEY_HEX": "02" * 32}
    )
    errors = validate_release_inputs(
        {
            "CS_PUBLIC_KEY": unrelated_public_key,
            "CS_SIGNING_PRIVATE_KEY_HEX": "01" * 32,
        }
    )
    assert any("does not match" in error for error in errors)


def test_preflight_runs_as_direct_workflow_script(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("CS_PUBLIC_KEY", None)
    env["CS_SIGNING_PRIVATE_KEY_HEX"] = "01" * 32

    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "mandatory release trust inputs are available" in result.stdout
