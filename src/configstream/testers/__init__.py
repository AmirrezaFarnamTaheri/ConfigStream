# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tester Facade.
Exposes testers from submodules.
"""

from .manager import SingBoxTester
from .go import GoBatchTester
from .utils import SecureConfigContext, _cleanup_temp_files

__all__ = [
    "SingBoxTester",
    "GoBatchTester",
    "SecureConfigContext",
    "_cleanup_temp_files",
]
