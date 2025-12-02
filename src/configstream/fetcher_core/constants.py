import os

# Allow override via env for low-memory environments
MAX_RESPONSE_SIZE = int(
    os.getenv("MAX_RESPONSE_SIZE", 50 * 1024 * 1024)
)  # Default 50 MB
