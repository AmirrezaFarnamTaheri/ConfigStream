"""
ConfigStream - VPN Configuration Aggregator

This package provides tools to fetch, test, and manage VPN configurations
from various sources.
"""

__version__ = "1.0.0"
__author__ = "Amirreza 'Farnam' Taheri"

# Use selector event loop on Windows to avoid proactor shutdown issues
import asyncio
import sys

if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:  # pragma: no cover - non-Windows platforms
        pass


# Lazy imports to avoid loading heavy dependencies when not needed
def __getattr__(name):
    """Lazy loading of package components to avoid unnecessary imports."""
    if name == "Proxy":
        from .models import Proxy

        return Proxy
    elif name == "SingBoxTester":
        from .testers import SingBoxTester

        return SingBoxTester
    elif name == "parse_config":
        from .core import parse_config

        return parse_config
    elif name == "run_full_pipeline":
        from .pipeline import run_full_pipeline

        return run_full_pipeline
    elif name == "AppSettings":
        from .config import AppSettings

        return AppSettings
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# Define the public API of the package
__all__ = [
    "Proxy",
    "SingBoxTester",
    "parse_config",
    "run_full_pipeline",
    "AppSettings",
    "__version__",
    "__author__",
]
