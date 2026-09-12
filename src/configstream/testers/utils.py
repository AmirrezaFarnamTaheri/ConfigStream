# SPDX-License-Identifier: AGPL-3.0-or-later
"""Private temporary configs with retryable cleanup."""

import atexit
import logging
import os
import stat
import tempfile
import threading
from contextlib import contextmanager
from typing import Iterator, Set

from ..security_validator import SecurityValidator

logger = logging.getLogger(__name__)
_TEMP_FILES: Set[str] = set()
_TEMP_FILES_LOCK = threading.Lock()


def _remove_temp_file(path: str) -> None:
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
    except OSError as exc:
        logger.warning(
            "Temporary config cleanup failed: %s",
            SecurityValidator.sanitize_log_message(str(exc)),
        )
        return  # Retain ownership so shutdown can retry.
    with _TEMP_FILES_LOCK:
        _TEMP_FILES.discard(path)


def _cleanup_temp_files() -> None:
    with _TEMP_FILES_LOCK:
        paths = tuple(_TEMP_FILES)
    for path in paths:
        _remove_temp_file(path)


atexit.register(_cleanup_temp_files)


@contextmanager
def SecureConfigContext(content: str) -> Iterator[str]:
    fd, path = tempfile.mkstemp(suffix=".json")
    with _TEMP_FILES_LOCK:
        _TEMP_FILES.add(path)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
            stream.write(content)
        yield path
    finally:
        _remove_temp_file(path)
