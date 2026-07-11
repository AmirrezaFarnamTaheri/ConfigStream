# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate that Bandit suppressions are narrow and auditable."""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess  # nosec B404
import sys
import tempfile
import tokenize
from pathlib import Path

ROOT = Path(__