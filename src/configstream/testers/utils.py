import atexit
import logging
import os
import stat
import tempfile
import threading
from contextlib import contextmanager
from typing import Set

logger = logging.getLogger(__name__)

_TEMP_FILES: Set[str] = set()
_TEMP_FILES_LOCK = threading.Lock()


def _cleanup_temp_files():
    for path in _TEMP_FILES:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except Exception:
            pass


atexit.register(_cleanup_temp_files)


@contextmanager
def SecureConfigContext(content: str):
    fd, path = tempfile.mkstemp(suffix=".json")
    with _TEMP_FILES_LOCK:
        _TEMP_FILES.add(path)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
        if not os.path.exists(path):
            raise OSError(f"Failed to create temp config file at {path}")
        logger.debug(f"Created temp config file: {path}")
        yield path
    finally:
        try:
            # os.unlink raises FileNotFoundError if file doesn't exist, which is fine
            os.unlink(path)
        except FileNotFoundError:
            pass
        except OSError as e:
            logger.warning(f"Failed to unlink temp file {path}: {e}")
        finally:
            with _TEMP_FILES_LOCK:
                _TEMP_FILES.discard(path)
            logger.debug(f"Cleaned up temp config file: {path}")
