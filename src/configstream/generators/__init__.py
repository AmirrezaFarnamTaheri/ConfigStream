# SPDX-License-Identifier: AGPL-3.0-or-later
from .base64 import generate_base64_subscription
from .clash import generate_clash_config
from .singbox import generate_singbox_config
from .split import generate_split_outputs

__all__ = [
    "generate_base64_subscription",
    "generate_clash_config",
    "generate_singbox_config",
    "generate_split_outputs",
]
