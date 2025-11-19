"""
Cleanup script to remove deprecated modules.
"""
import os
from pathlib import Path

DEPRECATED_FILES = [
    "src/configstream/proxies_standard.py", # If exists
    "src/configstream/validator.py", # Replaced by security_validator.py
    # Add any other files identified as dead code
]

def cleanup():
    for f in DEPRECATED_FILES:
        p = Path(f)
        if p.exists():
            print(f"Removing deprecated: {p}")
            p.unlink()
        else:
            print(f"Already clean: {p}")

if __name__ == "__main__":
    cleanup()
