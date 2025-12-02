"""
Output Generators.
Refactored into `src/configstream/generators/` for modularity.
This module now serves as a facade for backward compatibility.
"""

from .generators import (
    generate_base64_subscription,
    generate_clash_config,
    generate_singbox_config,
    generate_split_outputs,
)

__all__ = [
    "generate_base64_subscription",
    "generate_clash_config",
    "generate_singbox_config",
    "generate_split_outputs",
]
