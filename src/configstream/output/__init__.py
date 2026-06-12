# SPDX-License-Identifier: AGPL-3.0-or-later
"""
ConfigStream Output Package.
Modularized generators for metadata, public lists, native configs, and subscriptions.
"""

from .metadata import (
    generate_metadata_json,
    generate_health_json,
    write_public_artifact_contract,
)
from .public_lists import (
    generate_categorized_lists,
)
from .native_configs import (
    generate_quantumultx_profile,
    generate_surge_profile,
)
from .subscriptions import (
    generate_clash_subscription,
    generate_base64_subscription,
    generate_plaintext_subscription,
)

# Canonical full-config generators live in configstream.generators; re-export
# here so the output package exposes one cohesive surface.
from ..generators import (
    generate_singbox_config,
    generate_clash_config,
)

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
