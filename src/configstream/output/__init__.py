# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lazy output package exports for generators and artifact-contract helpers."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
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
]

_EXPORT_MAP = {
    "generate_metadata_json": (".metadata", "generate_metadata_json"),
    "generate_health_json": (".metadata", "generate_health_json"),
    "write_public_artifact_contract": (".metadata", "write_public_artifact_contract"),
    "generate_categorized_lists": (".public_lists", "generate_categorized_lists"),
    "generate_quantumultx_profile": (
        ".native_configs",
        "generate_quantumultx_profile",
    ),
    "generate_surge_profile": (".native_configs", "generate_surge_profile"),
    "generate_clash_subscription": (
        ".subscriptions",
        "generate_clash_subscription",
    ),
    "generate_base64_subscription": (
        ".subscriptions",
        "generate_base64_subscription",
    ),
    "generate_plaintext_subscription": (
        ".subscriptions",
        "generate_plaintext_subscription",
    ),
    "generate_singbox_config": ("..generators", "generate_singbox_config"),
    "generate_clash_config": ("..generators", "generate_clash_config"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attribute = _EXPORT_MAP[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    module = import_module(module_name, __name__)
    value = getattr(module, attribute)
    globals()[name] = value
    return value
