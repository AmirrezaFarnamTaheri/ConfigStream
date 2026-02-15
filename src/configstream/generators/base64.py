# SPDX-License-Identifier: AGPL-3.0-or-later
import base64
from typing import List
from ..models import Proxy
from .plaintext import generate_plaintext_subscription


def generate_base64_subscription(proxies: List[Proxy]) -> str:
    """Generates a base64 encoded subscription string.

    Never returns an empty string — if no URI-compatible proxies exist,
    a minimal placeholder is encoded so output files are always ≥ 1 byte.
    """
    content = generate_plaintext_subscription(proxies)
    if not content:
        content = "# no URI-compatible proxies in this run\n"
    return base64.b64encode(content.encode("utf-8")).decode("utf-8")
