#!/usr/bin/env python3
"""
Hugging Face Dataset Uploader for ConfigStream.
Mirrors the 'output/' directory to a Hugging Face Dataset repository.
"""

import os
import logging
import argparse
from pathlib import Path
from huggingface_hub import HfApi, upload_folder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def upload_to_hf(
    local_dir: str,
    repo_id: str,
    token: str,
    repo_type: str = "dataset",
    commit_message: str = "Update ConfigStream output",
):
    """
    Uploads a folder to Hugging Face.
    """
    if not os.path.exists(local_dir):
        logger.error(f"Local directory not found: {local_dir}")
        return

    logger.info(f"Uploading {local_dir} to {repo_id} ({repo_type})...")

    try:
        api = HfApi(token=token)

        # Ensure repo exists
        try:
            api.create_repo(repo_id=repo_id, repo_type=repo_type, exist_ok=True)
            logger.info(f"Repository {repo_id} confirmed.")
        except Exception as e:
            logger.warning(
                f"Repo check failed (might already exist or token permissions): {e}"
            )

        # Upload
        url = api.upload_folder(
            folder_path=local_dir,
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message=commit_message,
        )
        logger.info(f"Upload complete: {url}")

    except Exception as e:
        logger.error(f"Failed to upload to Hugging Face: {e}")
        # We generally don't want to fail the CI pipeline if the mirror fails,
        # unless strict mirroring is required.
        # sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Upload output to Hugging Face")
    parser.add_argument("--path", default="output", help="Path to output directory")
    parser.add_argument(
        "--repo-id", required=True, help="Hugging Face Repo ID (e.g., user/dataset)"
    )
    parser.add_argument("--token", help="HF API Token (or use HF_TOKEN env var)")
    parser.add_argument(
        "--repo-type",
        default="dataset",
        choices=["dataset", "model", "space"],
        help="Repository type",
    )

    args = parser.parse_args()

    token = args.token or os.environ.get("HF_TOKEN")
    if not token:
        logger.error(
            "No Hugging Face token provided. Set HF_TOKEN env var or use --token."
        )
        return

    upload_to_hf(
        local_dir=args.path, repo_id=args.repo_id, token=token, repo_type=args.repo_type
    )


if __name__ == "__main__":
    main()
