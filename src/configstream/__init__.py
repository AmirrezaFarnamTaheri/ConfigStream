# SPDX-License-Identifier: AGPL-3.0-or-later
"""
ConfigStream: High-Performance VPN Aggregator & Tester
"""

import logging

import sys
from typing import Any, Optional
import importlib.metadata

try:
    __version__ = importlib.metadata.version("configstream")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"

__author__ = "Amirreza 'Farnam' Taheri"

# pylint: disable=undefined-all-variable
__all__ = [
    "Proxy",
    "SingBoxTester",
    "parse_config",
    "run_full_pipeline",
    "AppSettings",
    "__version__",
    "__author__",
]


def __getattr__(name: str) -> Any:
    if name == "Proxy":
        from .models import Proxy

        return Proxy
    elif name == "SingBoxTester":
        from .testers import SingBoxTester

        return SingBoxTester
    elif name == "parse_config":
        from .auto_detect import auto_detect_and_parse

        return auto_detect_and_parse
    elif name == "run_full_pipeline":
        from .pipeline import run_full_pipeline

        return run_full_pipeline
    elif name == "AppSettings":
        from .config import AppSettings

        return AppSettings
    if not name or name.startswith("."):
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    try:
        return importlib.import_module(f".{name}", __name__)
    except (ImportError, ModuleNotFoundError):
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None


if sys.platform == "win32":
    import asyncio

    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _patch_sniffio_for_asyncio() -> None:
    """Work around sniffio detection failures on newer Python/asyncio combos."""
    try:
        import sniffio  # type: ignore
    except Exception:
        logging.getLogger(__name__).debug("Suppressed broad exception")
        return

    import asyncio

    if (
        getattr(sniffio.current_async_library, "__name__", "")
        == "_patched_async_library"
    ):
        return

    _orig = sniffio.current_async_library

    def _patched_async_library() -> str:
        try:
            return _orig()
        except sniffio.AsyncLibraryNotFoundError:
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                raise sniffio.AsyncLibraryNotFoundError(
                    "No running event loop"
                ) from None
            return "asyncio"

    sniffio.current_async_library = _patched_async_library  # type: ignore[assignment]


def _patch_anyio_current_task() -> None:
    """Work around anyio current_task returning None on newer Python/asyncio."""
    try:
        import anyio._backends._asyncio as anyio_asyncio  # type: ignore
    except Exception:
        logging.getLogger(__name__).debug("Suppressed broad exception")
        return

    import asyncio
    import weakref

    if getattr(anyio_asyncio.current_task, "__name__", "") == "_safe_current_task":
        return

    _orig_current_task = anyio_asyncio.current_task
    _sentinel_tasks: (
        "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Task]"
    ) = weakref.WeakKeyDictionary()

    async def _keepalive() -> None:
        await asyncio.Event().wait()

    def _safe_current_task(
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> Optional[asyncio.Task]:
        task = _orig_current_task(loop)
        if task is not None:
            return task
        try:
            running_loop = loop or asyncio.get_running_loop()
        except RuntimeError:
            return task
        sentinel = _sentinel_tasks.get(running_loop)
        if sentinel is None or sentinel.done():
            sentinel = running_loop.create_task(_keepalive())
            _sentinel_tasks[running_loop] = sentinel
        return sentinel

    anyio_asyncio.current_task = _safe_current_task


def _apply_compat_patches() -> None:
    """Apply sniffio/anyio compatibility patches.

    These patches work around detection failures in specific
    Python/asyncio version combinations (P3 / nest_asyncio elimination
    strategic item).  They are applied only when
    ``CONFIGSTREAM_COMPAT_PATCHES=1`` is set in the environment so that
    clean production deployments on supported runtimes do not carry
    unnecessary monkeypatches.  The test suite sets this variable via
    ``conftest.py`` for environments that still need it.

    Set ``CONFIGSTREAM_COMPAT_PATCHES=1`` to opt in.
    """
    import os

    if os.environ.get("CONFIGSTREAM_COMPAT_PATCHES", "").lower() in (
        "1",
        "true",
        "yes",
    ):
        _patch_sniffio_for_asyncio()
        _patch_anyio_current_task()


_apply_compat_patches()
