"""
Core Tester Implementation.
Refactored into `src/configstream/testers/` for modularity.
This module now serves as a facade for backward compatibility.
"""

from .testers.go import GoBatchTester
from .testers.manager import SingBoxTester
from .testers.utils import SecureConfigContext, _cleanup_temp_files

__all__ = [
    "SingBoxTester",
    "GoBatchTester",
    "SecureConfigContext",
    "_cleanup_temp_files",
]
