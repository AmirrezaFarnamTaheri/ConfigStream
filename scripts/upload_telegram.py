# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Telegram Upload Script
Uploads the latest proxy files to a Telegram Channel.
"""

import os
import httpx  # type: ignore
from pathlib import Path


def upload_to_telegram(token, chat_id, file_path, caption=""):
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    try:
        with open(file_path, "rb") as f:
            files = {"document": f}
            data = {"chat_id": chat_id, "caption": caption}
            response = httpx.post(url, files=files, data=data, timeout=60)
            response.raise_for_status()
            print(f"Successfully uploaded {file_path.name}")
    except Exception as e:
        print(f"Failed to upload {file_path.name}: {e}")


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    output_dir = Path("output")

    if not token or not chat_id:
        print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        return

    # Files to upload
    files = [
        output_dir / "singbox.json",
        output_dir / "clash.yaml",
        output_dir / "singbox-vpn.json",
        output_dir / "base64.txt",
        output_dir / "singbox-chains.json",
        output_dir / "revived.json",
    ]

    version = os.getenv("VERSION_TAG", "latest")
    caption = f"ConfigStream Update {version}"

    for f in files:
        if f.exists():
            upload_to_telegram(token, chat_id, f, caption)


if __name__ == "__main__":
    main()
