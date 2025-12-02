from typing import Any


def safe_int_conversion(value: Any, default: int = 0) -> int:
    """
    Safely convert a value to int, handling bytes and other types.
    """
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, bytes):
        try:
            return int(value.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            try:
                return int.from_bytes(value, byteorder="big", signed=False)
            except (ValueError, OverflowError):
                return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
