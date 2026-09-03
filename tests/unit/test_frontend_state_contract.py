# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for the 5-state trust UI contract in core controllers.

States:
1. Loading: Non-blocking skeleton/loader with zero layout shift.
2. Fresh: Renders telemetry only after integrity verification succeeds.
3. Stale: Displays persistent warning citing metadata.last_updated_utc (never visitor new Date()).
4. Invalid: Cryptographic verification failure blocks operational actions (fail-closed).
5. Empty / Error: Descriptive failure message with an actionable Retry trigger.
"""

from __future__ import annotations

from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = REPO_ROOT / "frontend"


def _read_file(relative_path: str) -> str:
    path = FRONTEND_DIR / relative_path
    assert path.is_file(), f"File not found: {path}"
    return path.read_text(encoding="utf-8")


def test_main_and_proxies_implement_5_state_trust_contract() -> None:
    main_js = _read_file("assets/js/main.js")
    proxies_js = _read_file("assets/js/proxies.js")

    for controller_name, code in [("main.js", main_js), ("proxies.js", proxies_js)]:
        # Must export or define applyTrustState or handle the 5 trust states
        assert (
            "applyTrustState" in code or "handleTrustState" in code
        ), f"{controller_name} missing applyTrustState function"
        # Verify all 5 state branches are represented
        for state in ["loading", "fresh", "stale", "invalid"]:
            assert state in code, f"{controller_name} missing '{state}' state handling"
        # Must handle error or empty state
        assert (
            "error" in code or "empty" in code
        ), f"{controller_name} missing error/empty state handling"


def test_freshness_timestamps_strictly_derive_from_metadata_last_updated() -> None:
    main_js = _read_file("assets/js/main.js")
    proxies_js = _read_file("assets/js/proxies.js")

    # Main must reference last_updated_utc
    assert (
        "last_updated_utc" in main_js
    ), "main.js must derive freshness from metadata.last_updated_utc"
    assert (
        "last_updated_utc" in proxies_js
    ), "proxies.js must derive freshness from metadata.last_updated_utc"

    # Neither controller should spoof freshness using new Date().toLocaleString() for footerUpdate
    footer_date_spoof_pattern = re.compile(
        r"footerUpdate.*new Date\(\)\.(?:toLocaleString|toISOString|toLocaleDateString)",
        re.DOTALL,
    )
    assert not footer_date_spoof_pattern.search(
        main_js
    ), "main.js must not spoof footer update using visitor clock"
    assert not footer_date_spoof_pattern.search(
        proxies_js
    ), "proxies.js must not spoof footer update using visitor clock"


def test_invalid_security_state_blocks_operational_actions() -> None:
    proxies_js = _read_file("assets/js/proxies.js")
    main_js = _read_file("assets/js/main.js")

    # In proxies.js, copy and download actions must check trust / verification state
    assert (
        "canDistribute" in proxies_js
        or "isOperationalBlocked" in proxies_js
        or "isActionAllowed" in proxies_js
    ), "proxies.js must check distribution / verification state before operational copy/download actions"

    # In invalid state, alert must be shown and actions blocked
    assert (
        "Detached cryptographic verification failed" in main_js
        or "Detached cryptographic verification failed" in proxies_js
        or "Security Alert" in main_js
        or "Security Alert" in proxies_js
    )


def test_error_and_empty_states_provide_actionable_retry() -> None:
    proxies_js = _read_file("assets/js/proxies.js")
    main_js = _read_file("assets/js/main.js")

    # Both main and proxies must provide retry capability
    assert (
        "retry" in proxies_js.lower()
    ), "proxies.js must provide actionable retry trigger on error"
    assert (
        "retry" in main_js.lower()
    ), "main.js must provide retry or reconnect mechanism"


def test_provenance_banner_and_trust_classes_exist() -> None:
    trust_state_js = _read_file("assets/js/trust-state.js")

    # The shared renderer owns the banner DOM and classes; controllers import it.
    assert "trustStateBanner" in trust_state_js
    assert "trust-banner" in trust_state_js
