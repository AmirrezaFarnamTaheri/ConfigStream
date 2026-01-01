import os

# Allow override via env for low-memory environments
# Default 200MB to support large repositories (e.g. ircfspace)
MAX_RESPONSE_SIZE = int(
    os.getenv("MAX_RESPONSE_SIZE", str(200 * 1024 * 1024))
)
