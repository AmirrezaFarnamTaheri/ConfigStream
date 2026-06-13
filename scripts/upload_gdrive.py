# SPDX-License-Identifier: AGPL-3.0-or-later
"""Google Drive mirror uploader with service-account and OAuth2 refresh support."""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive"]
GOOGLE_OAUTH2_URI = "https://oauth2.googleapis.com/token"


def _build_service(creds: Credentials):
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _authenticate_service_account() -> Credentials:
    creds_json = os.environ.get("GDRIVE_SA_JSON", "").strip()
    if not creds_json:
        raise ValueError("GDRIVE_SA_JSON not configured.")
    creds_dict = json.loads(creds_json)
    return service_account.Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES
    )


def _authenticate_oauth_refresh() -> Credentials:
    refresh_token = os.environ.get("GDRIVE_REFRESH_TOKEN", "").strip()
    client_id = os.environ.get("GDRIVE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GDRIVE_CLIENT_SECRET", "").strip()

    if not (refresh_token and client_id and client_secret):
        raise ValueError(
            "OAuth refresh credentials missing. Set GDRIVE_REFRESH_TOKEN, "
            "GDRIVE_CLIENT_ID, and GDRIVE_CLIENT_SECRET."
        )

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=GOOGLE_OAUTH2_URI,
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def authenticate():
    """Authenticate with service account first, then OAuth2 refresh fallback."""
    last_error: Exception | None = None

    try:
        creds = _authenticate_service_account()
        logger.info("Authenticated via service account.")
        return _build_service(creds), creds
    except Exception as exc:  # pragma: no cover - environment dependent
        last_error = exc
        logger.info("Service account auth unavailable: %s", exc)

    try:
        creds = _authenticate_oauth_refresh()
        logger.info("Authenticated via OAuth2 refresh token.")
        return _build_service(creds), creds
    except Exception as exc:  # pragma: no cover - environment dependent
        last_error = exc

    raise RuntimeError("Google Drive auth failed.") from last_error


def _execute_with_refresh(request, creds: Credentials):
    """Execute request and retry once after token refresh on auth errors."""
    try:
        return request.execute()
    except HttpError as error:
        status = int(getattr(getattr(error, "resp", None), "status", 0) or 0)
        if status not in (401, 403):
            raise
        logger.warning("Auth error %s from Google Drive API; refreshing token.", status)
        try:
            creds.refresh(Request())
        except RefreshError as refresh_error:
            raise RuntimeError(f"Token refresh failed: {refresh_error}") from error
        return request.execute()


def get_folder_files(service, folder_id: str, creds: Credentials) -> dict[str, str]:
    """List all files in the target folder for update-vs-create decisions."""
    files: dict[str, str] = {}
    page_token = None
    while True:
        response = _execute_with_refresh(
            service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                spaces="drive",
                fields="nextPageToken, files(id, name)",
                pageToken=page_token,
            ),
            creds,
        )

        for item in response.get("files", []):
            files[item["name"]] = item["id"]

        page_token = response.get("nextPageToken")
        if page_token is None:
            break
    return files


def upload_file(
    service,
    creds: Credentials,
    folder_id: str,
    file_path: str,
    existing_files: dict[str, str],
) -> None:
    """Upload or update a file in the destination folder."""
    file_name = os.path.basename(file_path)
    media = MediaFileUpload(file_path, resumable=True)

    try:
        if file_name in existing_files:
            file_id = existing_files[file_name]
            logger.info("Updating %s (ID: %s)", file_name, file_id)
            _execute_with_refresh(
                service.files().update(fileId=file_id, media_body=media, fields="id"),
                creds,
            )
        else:
            logger.info("Creating %s", file_name)
            file_metadata = {"name": file_name, "parents": [folder_id]}
            _execute_with_refresh(
                service.files().create(
                    body=file_metadata, media_body=media, fields="id"
                ),
                creds,
            )
    except HttpError as error:
        logger.error("Google Drive upload failed for %s: %s", file_name, error)


def main() -> int:
    parser = argparse.ArgumentParser(description="Mirror folder to Google Drive.")
    parser.add_argument("--path", required=True, help="Local folder to sync")
    parser.add_argument(
        "--folder-id", required=True, help="Google Drive target folder ID"
    )
    args = parser.parse_args()

    try:
        service, creds = authenticate()

        logger.info("Scanning remote folder...")
        existing_files = get_folder_files(service, args.folder_id, creds)

        local_path = Path(args.path)
        if not local_path.exists():
            logger.error("Local path %s does not exist.", local_path)
            return 1

        logger.info("Starting sync from %s", local_path)
        for item in local_path.glob("*"):
            if item.is_file():
                upload_file(
                    service,
                    creds,
                    args.folder_id,
                    str(item),
                    existing_files,
                )

        logger.info("Google Drive sync complete.")
        return 0
    except Exception as exc:
        err_msg = str(exc)
        secrets = [
            os.environ.get("GDRIVE_REFRESH_TOKEN"),
            os.environ.get("GDRIVE_CLIENT_SECRET"),
            os.environ.get("GDRIVE_SA_JSON"),
        ]
        for s in secrets:
            if s and s.strip() and s.strip() in err_msg:
                err_msg = err_msg.replace(s.strip(), "[REDACTED]")
        logger.error("Critical error: %s", err_msg)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
