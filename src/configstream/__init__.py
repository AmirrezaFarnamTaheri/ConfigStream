"""
ConfigStream: High-Performance VPN Aggregator & Tester
"""

import sys
import importlib.metadata

try:
    __version__ = importlib.metadata.version("configstream")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"

__author__ = "Amirreza 'Farnam' Taheri"

__all__ = [
    "Proxy",
    "SingBoxTester",
    "parse_config",
    "run_full_pipeline",
    "AppSettings",
    "__version__",
    "__author__",
]

def __getattr__(name: str):
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
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

if sys.platform == "win32":
    import asyncio
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
