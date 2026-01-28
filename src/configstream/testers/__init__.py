# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tester Facade.
Exposes testers from submodules.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import SingBoxTester
    from .go import GoBatchTester
    from .utils import SecureConfigContext, _cleanup_temp_files

__all__ = [
    "SingBoxTester",
    "GoBatchTester",
    "SecureConfigContext",
    "_cleanup_temp_files",
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
    if name == "_cleanup_temp_files":
        from .utils import _cleanup_temp_files as _cleanup_temp_files_impl

        return _cleanup_temp_files_impl
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
