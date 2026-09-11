# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import builtins
from collections.abc import Iterator
from typing import Any

import pytest

from scripts import resilient_stage


def _reset_cache() -> None:
    resilient_stage._PROJECT_SANITIZER = None
    resilient_stage._PROJECT_SANITIZER_RESOLVED = False
    resilient_stage._PROJECT_SANITIZER_WARNING_EMITTED = False


@pytest.fixture(autouse=True)
def _isolate_sanitizer_cache() -> Iterator[None]:
    _reset_cache()
    try:
        yield
    finally:
        _reset_cache()


def test_project_sanitizer_fallback_warns_once_and_masks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    def blocked_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "configstream.security_validator":
            raise ImportError("unavailable")
        return original_import(name, *args, **kwargs)

    warnings: list[str] = []
    monkeypatch.setattr(builtins, "__import__", blocked_import)
    monkeypatch.setattr(
        resilient_stage.logger,
        "warning",
        lambda message, *args: warnings.append(message % args),
    )

    first = resilient_stage._project_sanitize("token=secret-value")
    second = resilient_stage._project_sanitize("password=another-secret")

    assert "secret-value" not in first
    assert "another-secret" not in second
    assert len(warnings) == 1


def test_project_sanitizer_is_resolved_once() -> None:
    calls: list[str] = []

    def sanitizer(value: str) -> str:
        calls.append(value)
        return f"clean:{value}"

    resilient_stage._PROJECT_SANITIZER = sanitizer
    resilient_stage._PROJECT_SANITIZER_RESOLVED = True

    assert resilient_stage._project_sanitize("one") == "clean:one"
    assert resilient_stage._project_sanitize("two") == "clean:two"
    assert calls == ["one", "two"]
