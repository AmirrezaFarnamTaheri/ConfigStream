# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import builtins

from scripts import resilient_stage


def _reset_cache() -> None:
    resilient_stage._PROJECT_SANITIZER = None
    resilient_stage._PROJECT_SANITIZER_RESOLVED = False
    resilient_stage._PROJECT_SANITIZER_WARNING_EMITTED = False


def test_project_sanitizer_fallback_warns_once_and_masks(monkeypatch) -> None:
    _reset_cache()
    original_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "configstream.security.validator":
            raise ImportError("unavailable")
        return original_import(name, *args, **kwargs)

    warnings: list[str] = []
    monkeypatch.setattr(builtins, "__import__", blocked_import)
    monkeypatch.setattr(resilient_stage.LOGGER, "warning", lambda message, *args: warnings.append(message % args))

    first = resilient_stage._project_sanitize("token=secret-value")
    second = resilient_stage._project_sanitize("password=another-secret")

    assert "secret-value" not in first
    assert "another-secret" not in second
    assert len(warnings) == 1


def test_project_sanitizer_is_resolved_once(monkeypatch) -> None:
    _reset_cache()
    calls: list[str] = []

    def sanitizer(value: str) -> str:
        calls.append(value)
        return f"clean:{value}"

    resilient_stage._PROJECT_SANITIZER = sanitizer
    resilient_stage._PROJECT_SANITIZER_RESOLVED = True

    assert resilient_stage._project_sanitize("one") == "clean:one"
    assert resilient_stage._project_sanitize("two") == "clean:two"
    assert calls == ["one", "two"]
