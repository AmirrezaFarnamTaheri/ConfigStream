# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Verification tests for Task 3: Repository slop cleanup.

These tests act as regression guards — they verify that previously identified
dead code and unnecessary abstractions have been removed and that no regressions
were introduced in the modules that were cleaned up.
"""
import pytest
import importlib

import configstream.fetcher_worker as fw


# ---------------------------------------------------------------------------
# Negative tests: confirm dead code is absent
# ---------------------------------------------------------------------------

def test_unused_exception_classes_removed():
    """fetcher_worker.py must not contain any unused legacy exception classes."""
    assert not hasattr(fw, "UnusedLegacyFetcherError"), (
        "UnusedLegacyFetcherError should not exist in fetcher_worker.py"
    )


def test_no_dead_pass_through_wrappers():
    """fetcher_worker.py must not export dead or unused callables it defined itself."""
    # Allowed public symbols defined directly in fetcher_worker
    expected_own_symbols = {
        "FetchResult",
        "FetcherError",
        "RateLimitError",
        "parse_retry_after",
        "MAX_RESPONSE_SIZE",
    }
    unexpected_own = []
    for name in dir(fw):
        if name.startswith("_"):
            continue
        obj = getattr(fw, name)
        # Only flag callables that originate from fetcher_worker itself
        # (not stdlib/typing imports like Any, datetime, timezone, etc.)
        obj_module = getattr(obj, "__module__", None) or ""
        if "fetcher_worker" not in obj_module:
            continue
        if name not in expected_own_symbols:
            unexpected_own.append(name)
    assert not unexpected_own, (
        f"Unexpected own callables in fetcher_worker.py: {unexpected_own}. "
        "These should either be added to the expected set or removed as dead code."
    )


# ---------------------------------------------------------------------------
# Positive tests: confirm the core API still works
# ---------------------------------------------------------------------------

def test_fetch_result_construction():
    """FetchResult must remain constructable with minimal arguments."""
    result = fw.FetchResult(success=True, source="https://example.com/sub")
    assert result.success is True
    assert result.source == "https://example.com/sub"
    assert result.content == ""
    assert result.error is None


def test_rate_limit_error_with_retry_after():
    """RateLimitError must carry the retry_after attribute."""
    err = fw.RateLimitError(retry_after=30.0)
    assert err.retry_after == 30.0
    assert "30.0" in str(err)


def test_parse_retry_after_integer_string():
    """parse_retry_after must parse a plain integer string to float."""
    assert fw.parse_retry_after("120") == 120.0


def test_parse_retry_after_none_input():
    """parse_retry_after must return None for missing header."""
    assert fw.parse_retry_after(None) is None


def test_parse_retry_after_invalid_returns_none():
    """parse_retry_after must return None for unparseable values."""
    assert fw.parse_retry_after("garbage$$value") is None
