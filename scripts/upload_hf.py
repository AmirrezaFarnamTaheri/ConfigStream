"""
Hugging Face Upload Script
Uploads the output directory to a Hugging Face Dataset.
"""

import os
import sys
from huggingface_hub import HfApi


def main():
    token = os.getenv("HF_TOKEN")
    repo_id = os.getenv("HF_REPO_ID")
    output_dir = "output"

    if not token or not repo_id:
        print("Missing HF_TOKEN or HF_REPO_ID")
        sys.exit(1)

    api = HfApi(token=token)

    try:
        print(f"Uploading {output_dir} to {repo_id}...")
        api.upload_folder(
            folder_path=output_dir,
            repo_id=repo_id,
            repo_type="dataset",
            commit_message=f"Update proxies: {os.getenv('VERSION_TAG', 'auto')}",
        )
        print("Upload complete.")
    except Exception as e:
        print(f"Failed to upload to Hugging Face: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
