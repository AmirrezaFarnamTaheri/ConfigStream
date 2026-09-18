# SPDX-License-Identifier: AGPL-3.0-or-later
"""``configstream.output``'s ``__getattr__`` lazily resolves its public names
from submodules instead of importing them all eagerly. Existing tests all
import the submodules directly (``from configstream.output import
native_configs``), so the dispatcher itself -- the part that maps a name to
a submodule, imports it, and caches the result on the package -- was never
exercised."""

import sys

import pytest

import configstream.output as output_pkg


@pytest.mark.parametrize(
    "name",
    [
        "generate_metadata_json",
        "generate_health_json",
        "write_public_artifact_contract",
        "generate_categorized_lists",
        "generate_base64_subscription",
        "generate_plaintext_subscription",
        "generate_singbox_config",
        "generate_clash_config",
        "generate_quantumultx_profile",
        "generate_surge_profile",
        "generate_clash_subscription",
    ],
)
def test_every_declared_export_resolves_to_a_callable(name: str) -> None:
    # Force re-resolution even if a previous test already cached it.
    sys.modules["configstream.output"].__dict__.pop(name, None)
    value = getattr(output_pkg, name)
    assert callable(value)


def test_resolved_export_is_cached_on_the_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sys.modules["configstream.output"].__dict__.pop("generate_health_json", None)
    first = output_pkg.generate_health_json
    # Once resolved, it must be a plain attribute -- no re-import through
    # __getattr__ on the second access.
    assert "generate_health_json" in vars(output_pkg)
    assert getattr(output_pkg, "generate_health_json") is first


def test_unknown_attribute_raises_attribute_error() -> None:
    with pytest.raises(AttributeError, match="no attribute 'not_a_real_export'"):
        output_pkg.not_a_real_export
