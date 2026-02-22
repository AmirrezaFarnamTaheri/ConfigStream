# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for forensic pipeline artifact audit strict mode."""

from __future__ import annotations

from scripts.audit_pipeline_outputs import report_has_failures


def test_report_has_failures_accepts_clean_report() -> None:
    report = {
        "missing_expected": [],
        "json_configs": [
            {
                "path": "singbox-vpn.json",
                "json_valid": True,
                "sing_box_check": True,
            }
        ],
        "base64_lists": [{"path": "base64-dns-hardened.txt", "invalid_lines": 0}],
        "stego_assets": [{"path": "stealth_apple-touch-icon.png", "decoded": True}],
    }
    failed, reasons = report_has_failures(report)
    assert failed is False
    assert reasons == []


def test_report_has_failures_detects_invalid_outputs() -> None:
    report = {
        "missing_expected": ["singbox-dns-safe.json"],
        "json_configs": [
            {
                "path": "singbox-vpn.json",
                "json_valid": False,
                "sing_box_check": False,
            }
        ],
        "base64_lists": [{"path": "base64-dns-hardened.txt", "invalid_lines": 3}],
        "stego_assets": [
            {"path": "stealth_apple-touch-icon.png", "decoded": False, "error": "bad"}
        ],
    }
    failed, reasons = report_has_failures(report)
    assert failed is True
    assert reasons


def test_report_has_failures_ignores_missing_stego_key_by_default() -> None:
    report = {
        "missing_expected": [],
        "json_configs": [
            {"path": "singbox-vpn.json", "json_valid": True, "sing_box_check": True}
        ],
        "base64_lists": [],
        "stego_assets": [
            {
                "path": "stealth_apple-touch-icon.png",
                "decoded": False,
                "error": "STEGO_KEY/CONFIG_STREAM_KEY not provided",
            }
        ],
    }
    failed, _ = report_has_failures(report)
    assert failed is False

    failed_strict, reasons = report_has_failures(report, strict_stego_key=True)
    assert failed_strict is True
    assert reasons
