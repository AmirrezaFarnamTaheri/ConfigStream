# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tester package.
Exposes testers via lazy imports to avoid heavy startup costs.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import SingBoxTester
    from .go import GoBatchTester
    from .utils import SecureConfigContext

__all__ = [
    "SingBoxTester",
    "GoBatchTester",
    "SecureConfigContext",
]


def __getattr__(name: str):
    if name == "SingBoxTester":
        from .manager import SingBoxTester as _SingBoxTester

        return _SingBoxTester
    if name == "GoBatchTester":
        from .go import GoBatchTester as _GoBatchTester

        return _GoBatchTester
    if name == "SecureConfigContext":
        from .utils import SecureConfigContext as _SecureConfigContext

        return _SecureConfigContext
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
