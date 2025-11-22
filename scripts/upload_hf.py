#!/usr/bin/env python3
"""
Uploads the output directory to Hugging Face Datasets.
Acts as an "S3 Bucket" mirror.
"""

import os
import logging
from pathlib import Path
from huggingface_hub import HfApi, upload_folder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hf_upload")

HF_TOKEN = os.getenv("HF_TOKEN")
REPO_ID = os.getenv("HF_REPO_ID") # e.g., "username/configstream-data"
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))

def main():
    if not HF_TOKEN or not REPO_ID:
        logger.warning("Hugging Face credentials not found. Skipping upload.")
        return

    logger.info(f"Uploading {OUTPUT_DIR} to {REPO_ID}...")
    try:
        api = HfApi(token=HF_TOKEN)

        # Ensure repo exists (private by default if creating)
        api.create_repo(repo_id=REPO_ID, repo_type="dataset", exist_ok=True)

        upload_folder(
            folder_path=str(OUTPUT_DIR),
            repo_id=REPO_ID,
            repo_type="dataset",
            path_in_repo=".",
            token=HF_TOKEN,
            commit_message=f"Update configs: {os.getenv('GITHUB_SHA', 'local')[:7]}"
        )
        logger.info("Upload complete.")
    except Exception as e:
        logger.error(f"Failed to upload to Hugging Face: {e}")
        # Don't exit with error to avoid breaking the pipeline, as this is a mirror

if __name__ == "__main__":
    main()
