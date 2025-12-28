"""
Tester Facade.
Exposes testers from submodules.
"""

from .go import GoBatchTester
from .manager import SingBoxTester
from .utils import SecureConfigContext, _cleanup_temp_files

__all__ = [
    "SingBoxTester",
    "GoBatchTester",
    "SecureConfigContext",
    "_cleanup_temp_files",
]
