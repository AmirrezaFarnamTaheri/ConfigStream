"""
Google Drive Mirror Script
Syncs a local directory to a specific Google Drive folder.
Uses Service Account for zero-interaction auth.
"""

# pylint: disable=import-error

import os
import json
import logging
import argparse
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Configure Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive"]


def authenticate():
    """Authenticate using Service Account JSON from Env Var."""
    creds_json = os.environ.get("GDRIVE_SA_JSON")
    if not creds_json:
        raise ValueError("GDRIVE_SA_JSON environment variable not set.")

    creds_dict = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def get_folder_files(service, folder_id):
    """List all files in the target folder to check for existing ones."""
    files = {}
    page_token = None
    while True:
        response = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and trashed=false",
                spaces="drive",
                fields="nextPageToken, files(id, name)",
                pageToken=page_token,
            )
            .execute()
        )

        for file in response.get("files", []):
            files[file["name"]] = file["id"]

        page_token = response.get("nextPageToken", None)
        if page_token is None:
            break
    return files


def upload_file(service, folder_id, file_path, existing_files):
    """Uploads or Updates a file."""
    file_name = os.path.basename(file_path)
    media = MediaFileUpload(file_path, resumable=True)

    try:
        if file_name in existing_files:
            # UPDATE existing file (Preserves File ID/Link)
            file_id = existing_files[file_name]
            logger.info("🔄 Updating %s (ID: %s)...", file_name, file_id)
            service.files().update(
                fileId=file_id, media_body=media, fields="id"
            ).execute()
        else:
            # CREATE new file
            logger.info("nw Creating %s...", file_name)
            file_metadata = {"name": file_name, "parents": [folder_id]}
            service.files().create(
                body=file_metadata, media_body=media, fields="id"
            ).execute()

    except HttpError as error:
        logger.error("❌ Error uploading %s: %s", file_name, error)


def main():
    parser = argparse.ArgumentParser(description="Mirror folder to Google Drive.")
    parser.add_argument("--path", required=True, help="Local folder to sync")
    parser.add_argument(
        "--folder-id", required=True, help="Google Drive Target Folder ID"
    )
    args = parser.parse_args()

    try:
        service = authenticate()

        # 1. Map existing remote files
        logger.info("🔍 Scanning remote folder...")
        existing_files = get_folder_files(service, args.folder_id)

        # 2. Walk local folder and upload
        local_path = Path(args.path)
        if not local_path.exists():
            logger.error("Local path %s does not exist.", local_path)
            return

        logger.info("🚀 Starting sync from %s...", local_path)

        # Upload files in the root of the output directory
        # (Recursive logic can be added if you have nested folders)
        for item in local_path.glob("*"):
            if item.is_file():
                upload_file(service, args.folder_id, str(item), existing_files)

        logger.info("✅ Google Drive Sync Complete.")

    except Exception as e:
        logger.error("Critical Error: %s", e)
        exit(1)


if __name__ == "__main__":
    main()
