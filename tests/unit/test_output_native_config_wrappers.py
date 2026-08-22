# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from typing import Any

import pytest

from configstream import generators
from configstream.output import native_configs


def test_singbox_wrapper_delegates_to_canonical_generator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Any, ...]] = []

    def generate(*args: Any) -> str:
        calls.append(args)
        return "singbox"

    monkeypatch.setattr(generators, "generate_singbox_config", generate)

    assert (
        native_configs.generate_singbox_config([], "eu", [{"type": "direct"}])
        == "singbox"
    )
    assert calls == [([], "eu", [{"type": "direct"}])]


def test_clash_wrapper_delegates_to_canonical_generator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Any, ...]] = []

    def generate(*args: Any) -> str:
        calls.append(args)
        return "clash"

    monkeypatch.setattr(generators, "generate_clash_config", generate)

    assert (
        native_configs.generate_clash_config(
            [], [{"type": "direct"}], {"servers": []}, True
        )
        == "clash"
    )
    assert calls == [([], [{"type": "direct"}], {"servers": []}, True)]
