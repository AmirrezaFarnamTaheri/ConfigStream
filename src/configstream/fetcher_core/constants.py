# SPDX-License-Identifier: AGPL-3.0-or-later
import os

# Allow override via env for low-memory environments
# Default 50MB. Large sources should be processed via streaming.
MAX_RESPONSE_SIZE = int(
    os.getenv("MAX_RESPONSE_SIZE", str(50 * 1024 * 1024))
)
