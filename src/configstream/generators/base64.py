# SPDX-License-Identifier: AGPL-3.0-or-later
import base64
from typing import List
from ..models import Proxy
from .plaintext import generate_plaintext_subscription


def generate_base64_subscription(proxies: List[Proxy]) -> str:
    """Generates a base64 encoded subscription string."""
    content = generate_plaintext_subscription(proxies)
    return base64.b64encode(content.encode("utf-8")).decode("utf-8")
