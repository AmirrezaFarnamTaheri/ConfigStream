# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for WebSocket origin validation (P2-13 fix coverage)."""

from unittest.mock import _patch as _PatchType
from unittest.mock import patch

from configstream.server.ws import _is_allowed_origin


# ---------------------------------------------------------------------------
# _is_allowed_origin unit tests
# ---------------------------------------------------------------------------


class _MockSettings:
    """Minimal settings stub used in tests."""

    def __init__(
        self, allowed_origins: str = "", allowed_origin_regex: str = ""
    ) -> None:
        self.ALLOWED_ORIGINS = allowed_origins
        self.ALLOWED_ORIGIN_REGEX = allowed_origin_regex


def _patch_settings(settings_obj: _MockSettings) -> _PatchType:
    return patch("configstream.server.ws.settings", settings_obj)


def test_allowed_origin_accepted() -> None:
    """An origin in the allow-list must return True."""
    s = _MockSettings("http://localhost:8000,http://localhost:3000")
    with _patch_settings(s):
        assert _is_allowed_origin("http://localhost:8000") is True
        assert _is_allowed_origin("http://localhost:3000") is True


def test_disallowed_origin_rejected() -> None:
    """An origin not in the allow-list must return False."""
    s = _MockSettings("http://localhost:8000")
    with _patch_settings(s):
        assert _is_allowed_origin("https://evil.example.com") is False


def test_absent_origin_rejected() -> None:
    """A missing (None) origin header must return False."""
    s = _MockSettings("http://localhost:8000")
    with _patch_settings(s):
        assert _is_allowed_origin(None) is False


def test_empty_string_origin_rejected() -> None:
    """An empty string origin must return False."""
    s = _MockSettings("http://localhost:8000")
    with _patch_settings(s):
        assert _is_allowed_origin("") is False


def test_regex_origin_accepted() -> None:
    """An origin matching ALLOWED_ORIGIN_REGEX must return True."""
    s = _MockSettings(
        allowed_origins="http://localhost:8000",
        allowed_origin_regex=r"https://[a-z0-9-]+\.example\.com",
    )
    with _patch_settings(s):
        assert _is_allowed_origin("https://staging.example.com") is True
        assert _is_allowed_origin("https://prod.example.com") is True


def test_regex_non_matching_rejected() -> None:
    """An origin that does NOT match ALLOWED_ORIGIN_REGEX must return False."""
    s = _MockSettings(
        allowed_origins="",
        allowed_origin_regex=r"https://[a-z0-9-]+\.example\.com",
    )
    with _patch_settings(s):
        assert _is_allowed_origin("https://evil.attacker.com") is False


def test_invalid_regex_does_not_raise() -> None:
    """A broken ALLOWED_ORIGIN_REGEX must not crash; origin is rejected."""
    s = _MockSettings(
        allowed_origins="",
        allowed_origin_regex=r"[invalid(regex",
    )
    with _patch_settings(s):
        result = _is_allowed_origin("http://localhost:8000")
        assert result is False


def test_whitespace_in_allowed_origins_stripped() -> None:
    """Origins with surrounding whitespace in the config must still match."""
    s = _MockSettings("  http://localhost:8000 , http://127.0.0.1:8000  ")
    with _patch_settings(s):
        assert _is_allowed_origin("http://localhost:8000") is True
        assert _is_allowed_origin("http://127.0.0.1:8000") is True


# ---------------------------------------------------------------------------
# Proxy.id normalization (P1-5 fix coverage)
# ---------------------------------------------------------------------------


def test_proxy_id_always_16_chars() -> None:
    """Proxy.id must always be a 16-char hex string, not a raw UUID."""
    from configstream.models import Proxy

    p_with_uuid = Proxy(
        config="vless://test",
        protocol="vless",
        address="1.2.3.4",
        port=443,
        uuid="550e8400-e29b-41d4-a716-446655440000",
    )
    id_val = p_with_uuid.id
    assert len(id_val) == 16, (
        f"Expected 16-char hex id, got {len(id_val)!r}: {id_val!r}"
    )
    int(id_val, 16)


def test_proxy_id_same_for_equivalent_proxies() -> None:
    """Two logically identical proxies must produce the same id."""
    from configstream.models import Proxy

    first = Proxy(
        config="vmess://test",
        protocol="vmess",
        address="10.0.0.1",
        port=1080,
        uuid="abc123",
    )
    second = Proxy(
        config="vmess://test",
        protocol="vmess",
        address="10.0.0.1",
        port=1080,
        uuid="abc123",
    )
    assert first.id == second.id


def test_proxy_id_different_for_different_proxies() -> None:
    """Different proxy endpoints must produce different ids."""
    from configstream.models import Proxy

    p1 = Proxy(config="x", protocol="vmess", address="1.1.1.1", port=80, uuid="aaa")
    p2 = Proxy(config="x", protocol="vmess", address="2.2.2.2", port=80, uuid="bbb")
    assert p1.id != p2.id
