# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Any


def parse_bool(value: Any) -> bool:
    """
    Safely parse boolean values from various types (str, int, bool).
    Returns True for "true", "1", "yes", etc. (case-insensitive).
    Returns False for empty string, None, "false", "0", "no".
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0

    s = str(value).lower().strip()
    if s in ("true", "1", "yes", "on"):
        return True
    return False
