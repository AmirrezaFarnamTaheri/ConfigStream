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

# Import key components to be available at the package level
from .models import Proxy
from .testers import SingBoxTester
from .core import parse_config
from .pipeline import run_full_pipeline
from .config import AppSettings

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
