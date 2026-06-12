# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Backward-compatible forwarder for legacy producer attributes.
"""

from configstream.pipeline.fetcher import fetch_multiple_sources
from configstream.async_file_ops import read_multiple_files_async

__all__ = ["fetch_multiple_sources", "read_multiple_files_async"]
