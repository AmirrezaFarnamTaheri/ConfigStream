# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Core Tester Implementation.
Refactored into `src/configstream/testers/` for modularity.
This module now serves as a facade for backward compatibility.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .testers.manager import SingBoxTester
    from .testers.go import GoBatchTester
    from .testers.utils import SecureConfigContext, _cleanup_temp_files

__all__ = [
    "SingBoxTester",
    "GoBatchTester",
    "SecureConfigContext",
    "_cleanup_temp_files",
]


def __getattr__(name: str):
    if name == "SingBoxTester":
        from .testers.manager import SingBoxTester as _SingBoxTester

        return _SingBoxTester
    if name == "GoBatchTester":
        from .testers.go import GoBatchTester as _GoBatchTester

        return _GoBatchTester
    if name == "SecureConfigContext":
        from .testers.utils import SecureConfigContext as _SecureConfigContext

        return _SecureConfigContext
    if name == "_cleanup_temp_files":
        from .testers.utils import _cleanup_temp_files as _cleanup_temp_files_impl

        return _cleanup_temp_files_impl
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
