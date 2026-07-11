# SPDX-License-Identifier: AGPL-3.0-or-later
"""Go tester package with a single verified process-launching implementation."""

from . import manager as _manager
from .secure_manager import GoBatchTester

# Python executes this package initializer before resolving
# ``configstream.testers.go_tester.manager``. Rebinding the module attribute
# ensures direct submodule imports receive the verified launcher too, while the
# secure subclass retains its private reference to the streaming base class.
_manager.GoBatchTester = GoBatchTester

__all__ = ["GoBatchTester"]
