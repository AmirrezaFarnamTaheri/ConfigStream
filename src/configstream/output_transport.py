# SPDX-License-Identifier: AGPL-3.0-or-later
"""Serialization and durable file I/O for public proxy data."""

import gzip
import json
import logging
import os
import re
from pathlib import Path
from typing import List, Optional

from .history.tracker import ProxyHistoryTracker
from .models import Proxy
from .serialize import serialize_proxy
from .utils import AtomicFileWriter

logger = logging.getLogger(__name__)


def save_json(
    proxies: List[Proxy],
    path: Path,
    compress: bool = False,
    history: Optional["ProxyHistoryTracker"] = None,
) -> None:
    """Save a JSON array of public proxy records atomically."""

    if not isinstance(proxies, list):
        proxies = [proxies] if proxies is not None else []
    if history is None:
        history = ProxyHistoryTracker()
        owns_history = True
    else:
        owns_history = False
    try:
        data = [serialize_proxy(proxy, history.get_history(proxy.id)) for proxy in proxies]
    finally:
        if owns_history:
            history.close()
    if not isinstance(data, list):
        data = [data]
    json_content = json.dumps(data, indent=2, ensure_ascii=False)
    AtomicFileWriter.write_text(path, json_content)

    if compress:
        gz_path = Path(str(path) + ".gz")
        temporary = gz_path.with_suffix(gz_path.suffix + ".tmp")
        try:
            with gzip.open(temporary, "wt", encoding="utf-8") as handle:
                handle.write(json_content)
            os.replace(temporary, gz_path)
        except Exception as exc:
            logger.error("Gzip compression failed for %s: %s", path, exc)
            temporary.unlink(missing_ok=True)
            raise


def inject_stego_key_into_frontend(secret_key: str, js_file_path: Path) -> None:
    """Compatibility shim that guarantees no symmetric key is published.

    Older output code called this function to place a decryption key in the same
    public JavaScript bundle as encrypted data.  That is obfuscation, not
    confidentiality.  The function now removes any existing literal key and
    never writes the supplied secret.  Confidential delivery must use an
    authenticated endpoint or recipient public-key encryption.
    """

    if not js_file_path.exists():
        logger.warning("Frontend JS not found at %s; no key cleanup required", js_file_path)
        return

    if secret_key:
        logger.warning(
            "Refusing to embed a symmetric secret in public frontend %s",
            js_file_path.name,
        )

    content = js_file_path.read_text(encoding="utf-8")
    pattern = r'(const\s+SECRET_KEY\s*=\s*")([^"]*)(")'
    new_content, replacements = re.subn(pattern, r'\1\3', content)
    if replacements:
        AtomicFileWriter.write_text(js_file_path, new_content)
        logger.info("Removed %d embedded frontend secret key(s)", replacements)
