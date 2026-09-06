# SPDX-License-Identifier: AGPL-3.0-or-later
"""Production-facing tester configuration policy."""

from __future__ import annotations

from ..config import AppSettings
from .manager import SingBoxTester as _BaseSingBoxTester


class SingBoxTester(_BaseSingBoxTester):
    """Honor STRICT_SECURITY for package-level production construction.

    The pipeline historically passed its API default ``False`` explicitly,
    bypassing the safer application setting. Treat the application setting as
    a security floor: callers can opt in explicitly, while disabling it requires
    setting ``STRICT_SECURITY=false`` in application configuration.
    """

    def __init__(self, *args, **kwargs):
        configured = bool(AppSettings().STRICT_SECURITY)
        requested = bool(kwargs.get("strict_security", False))
        kwargs["strict_security"] = configured or requested
        super().__init__(*args, **kwargs)
