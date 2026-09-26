# SPDX-License-Identifier: AGPL-3.0-or-later
"""Preflight must never block publication on optional key material.

The degradation matrix itself lives in ``tests/unit/test_signing_config.py``;
this module pins the preflight entry point's contract.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from scripts.preflight_release_inputs import validate_release_inputs
from scripts.validate_frontend_placeholders import _resolve_public_key

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "preflight_release_inputs.py"
SEED = "01" * 32


def test_preflight_accepts_public_key_derived_from_signing_key() -> None:
    assert validate_release_inputs({"CS_SIGNING_PRIVATE_KEY_HEX": SEED}) == []


def test_preflight_accepts_matching_explicit_public_and_signing_key() -> None:
    public_key = _resolve_public_key({"CS_SIGNING_PRIVATE_KEY_HEX": SEED})

    assert (
        validate_release_inputs(
            {
                "CS_PUBLIC_KEY": public_key,
                "CS_SIGNING_PRIVATE_KEY_HEX": SEED,
            }
        )
        == []
    )


def test_preflight_accepts_unsigned_release_by_default() -> None:
    assert validate_release_inputs({}) == []


def test_preflight_degrades_instead_of_rejecting_unusable_key_material() -> None:
    """Availability contract: a broken optional secret is a warning, not a stop."""

    public_key = _resolve_public_key({"CS_SIGNING_PRIVATE_KEY_HEX": "02" * 32})
    unusable_pairs = [
        {"CS_PUBLIC_KEY": public_key},
        {"CS_PUBLIC_KEY": "not-an-ed25519-key"},
        {"CS_SIGNING_PRIVATE_KEY_HEX": "not-hex"},
        {
            "CS_PUBLIC_KEY": public_key,
            "CS_SIGNING_PRIVATE_KEY_HEX": SEED,
        },
    ]

    for env in unusable_pairs:
        assert validate_release_inputs(env) == [], env


def test_preflight_runs_as_direct_workflow_script_without_signing_keys(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.pop("CS_PUBLIC_KEY", None)
    env.pop("CS_SIGNING_PRIVATE_KEY_HEX", None)
    env.pop("CONFIGSTREAM_SIGNING_PRIVATE_KEY_HEX", None)

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
    assert "does not depend on optional secrets" in result.stdout
    # The degradation reason is recorded rather than silently swallowed.
    assert "WARN" in result.stderr
