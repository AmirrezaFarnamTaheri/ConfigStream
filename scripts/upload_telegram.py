#!/usr/bin/env python3
"""
Uploads generated artifacts to a Telegram Channel.
Uses a simple HTTP POST to avoid heavy dependencies.
"""

import os
import sys
import requests
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telegram_upload")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))

def upload_file(filepath: Path):
    if not filepath.exists():
        logger.warning(f"File not found: {filepath}")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"

    logger.info(f"Uploading {filepath.name}...")
    try:
        with open(filepath, "rb") as f:
            files = {"document": f}
            data = {"chat_id": CHAT_ID, "caption": f"ConfigStream Release: {filepath.name}"}
            resp = requests.post(url, files=files, data=data, timeout=60)
            resp.raise_for_status()
            logger.info("Success.")
    except Exception as e:
        logger.error(f"Failed to upload {filepath.name}: {e}")

def main():
    if not BOT_TOKEN or not CHAT_ID:
        logger.warning("Telegram credentials not found. Skipping upload.")
        return

    # List of critical files to upload
    files_to_upload = [
        "singbox.json",
        "singbox-vpn.json",
        "singbox-chains.json",
        "clash.yaml",
        "proxies.json.gz"
    ]

    for fname in files_to_upload:
        upload_file(OUTPUT_DIR / fname)

if __name__ == "__main__":
    main()
