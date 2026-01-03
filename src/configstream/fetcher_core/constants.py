# SPDX-License-Identifier: AGPL-3.0-or-later
# Allow override via env for low-memory environments
# Default 200MB to support large repositories (e.g. ircfspace)
# Now managed via AppSettings in config.py
MAX_RESPONSE_SIZE = 200 * 1024 * 1024
