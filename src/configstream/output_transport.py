# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Output Transport Module.
Handles serialization and file I/O for proxy data.
"""

import gzip
import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Union
from .models import Proxy
from .history.tracker import ProxyHistoryTracker
from .serialize import serialize_proxy
from .utils import AtomicFileWriter

logger = logging.getLogger(__name__)


def save_json(proxies: List[Proxy], path: Path, compress: bool = False) -> None:
    """
    Save list of proxies to JSON file atomically with fsync for durability.
    """
    history = ProxyHistoryTracker()  # Singleton access
    data = [serialize_proxy(p, history.get_history(p.id)) for p in proxies]
    # Ensure proper JSON formatting (single JSON array, not concatenated objects)
    json_content = json.dumps(data, indent=2, ensure_ascii=False)

    AtomicFileWriter.write_text(path, json_content)

    if compress:
        gz_path = Path(str(path) + ".gz")
        temp_gz_path = gz_path.with_suffix(gz_path.suffix + ".tmp")
        try:
            with gzip.open(temp_gz_path, "wt", encoding="utf-8") as f:
                f.write(json_content)
            os.replace(temp_gz_path, gz_path)
        except gzip.BadGzipFile as e:
            # Gzip format errors
            logger.error(f"Gzip compression error for {path}: {e}")
            if temp_gz_path.exists():
                temp_gz_path.unlink()
            raise
        except (OSError, IOError) as e:
            # File system errors (permissions, disk space, etc.)
            logger.error(f"I/O error during gzip compression of {path}: {e}")
            if temp_gz_path.exists():
                temp_gz_path.unlink()
            raise
        except Exception as e:
            # Unexpected errors - cleanup and re-raise with context
            logger.exception(f"Unexpected error compressing {path}: {e}")
            if temp_gz_path.exists():
                temp_gz_path.unlink()
            raise


def save_metadata(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    stats: Dict[str, Union[int, float]], proxies: List[Proxy], output_dir: Path
) -> None:
    """
    Save metadata.json with statistics for the frontend.
    """
    from .output_logic import save_metadata as save_metadata_v2

    logger.warning(
        "output_transport.save_metadata is deprecated; delegating to output_logic.save_metadata."
    )
    save_metadata_v2(stats, proxies, output_dir)


def inject_stego_key_into_frontend(secret_key: str, js_file_path: Path) -> None:
    """
    Self-Healing Mechanism:
    Opens the frontend JavaScript file and implants the dynamic secret key
    so the browser can decrypt the latest steganography image.
    """
    if not js_file_path.exists():
        logger.warning(
            f"Frontend JS not found at {js_file_path}, skipping key injection."
        )
        return

    try:
        content = js_file_path.read_text(encoding="utf-8")

        # Regex to find: const SECRET_KEY = "ANYTHING_HERE";
        pattern = r'(const\s+SECRET_KEY\s*=\s*")([^"]*)(")'

        # FIX: Escape the key for safe JavaScript string injection
        # This prevents issues if the key contains backslashes or quotes
        import json

        escaped_key = json.dumps(secret_key)[1:-1]  # Remove outer quotes from JSON

        # Use a replacement function to avoid regex interpretation of special chars
        # in the secret_key (e.g., base64 Fernet keys can contain sequences like
        # backslash+digits that would be interpreted as backreferences like \17)
        def replacer(match):
            return match.group(1) + escaped_key + match.group(3)

        new_content = re.sub(pattern, replacer, content)

        # Atomic write to prevent corruption
        AtomicFileWriter.write_text(js_file_path, new_content)
        logger.info(f"✅ Successfully injected new Stego Key into {js_file_path.name}")

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"Failed to inject Stego Key: {e}")
