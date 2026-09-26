# SPDX-License-Identifier: AGPL-3.0-or-later
"""The optional signing keypair must degrade, never block publication."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from configstream.signer import Signer, normalize_public_key_hex
from configstream.signing_config import resolve_signing_material, usable_signing_key
from scripts.preflight_release_inputs import validate_release_inputs
from scripts.validate_frontend_placeholders import _resolve_public_key

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "preflight_release_inputs.py"
SEED = "01" * 32
OTHER_SEED = "02" * 32


def _pair(seed: str = SEED) -> dict[str, str]:
    return {
        "CS_SIGNING_PRIVATE_KEY_HEX": seed,
        "CS_PUBLIC_KEY": _resolve_public_key({"CS_SIGNING_PRIVATE_KEY_HEX": seed}),
    }


def test_no_secrets_degrades_to_unsigned() -> None:
    material = resolve_signing_material({})

    assert material.active is False
    assert material.state == "unsigned"
    assert material.signing_key == ""
    assert material.notes  # the reason is recorded, never silent


def test_matching_pair_is_active() -> None:
    material = resolve_signing_material(_pair())

    assert material.active is True
    assert material.state == "signed"
    assert material.signing_key == SEED
    assert material.public_key == normalize_public_key_hex(
        Signer(SEED).get_public_key_hex()
    )


def test_usable_private_key_without_anchor_derives_its_own() -> None:
    material = resolve_signing_material({"CS_SIGNING_PRIVATE_KEY_HEX": SEED})

    assert material.active is True
    assert material.public_key == normalize_public_key_hex(
        Signer(SEED).get_public_key_hex()
    )


@pytest.mark.parametrize(
    ("env", "expected_note"),
    [
        (
            {"CS_SIGNING_PRIVATE_KEY_HEX": "not-hex"},
            "not a valid Ed25519 key",
        ),
        (
            {"CS_SIGNING_PRIVATE_KEY_HEX": "01" * 8},
            "not a valid Ed25519 key",
        ),
        (
            {"CS_PUBLIC_KEY": "not-an-ed25519-key"},
            "not a valid Ed25519 public key",
        ),
    ],
)
def test_malformed_material_degrades_with_a_reason(
    env: dict[str, str], expected_note: str
) -> None:
    material = resolve_signing_material(env)

    assert material.active is False
    assert any(expected_note in note for note in material.notes)
    assert validate_release_inputs(env) == []


def test_anchor_without_signing_key_degrades() -> None:
    material = resolve_signing_material({"CS_PUBLIC_KEY": _pair()["CS_PUBLIC_KEY"]})

    assert material.active is False
    assert material.signing_key == ""
    assert any("no usable signing key" in note for note in material.notes)


def test_mismatched_pair_degrades_instead_of_signing_with_the_wrong_anchor() -> None:
    env = {
        "CS_SIGNING_PRIVATE_KEY_HEX": SEED,
        "CS_PUBLIC_KEY": _resolve_public_key(
            {"CS_SIGNING_PRIVATE_KEY_HEX": OTHER_SEED}
        ),
    }

    material = resolve_signing_material(env)

    assert material.active is False
    assert material.signing_key == ""
    assert any("does not match" in note for note in material.notes)
    # The critical safety property: an unusable pair must never produce a
    # signature the deploy side would then be unable to verify.
    assert usable_signing_key(env) == ""


def test_legacy_private_key_alias_is_accepted() -> None:
    material = resolve_signing_material({"CONFIGSTREAM_SIGNING_PRIVATE_KEY_HEX": SEED})

    assert material.active is True


def test_preflight_cli_reports_degraded_without_failing() -> None:
    env = os.environ.copy()
    for name in (
        "CS_PUBLIC_KEY",
        "CS_SIGNING_PRIVATE_KEY_HEX",
        "CONFIGSTREAM_SIGNING_PRIVATE_KEY_HEX",
    ):
        env.pop(name, None)

    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=SCRIPT.parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "does not depend on optional secrets" in result.stdout


def test_preflight_cli_prints_signing_configured_flag() -> None:
    env = os.environ.copy()
    env.update(_pair())

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--print-signing-configured"],
        cwd=SCRIPT.parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "true"
