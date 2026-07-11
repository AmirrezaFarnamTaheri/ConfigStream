# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sanitized, batched JSONL pipeline event persistence."""

import asyncio
import json
import logging
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any, Dict

from configstream.security_validator import SecurityValidator
from configstream.utils import _FileLock

EVENT_LOG_FILENAME = "pipeline_events