# SPDX-License-Identifier: AGPL-3.0-or-later
import base64
from typing import List
from ..models import Proxy
from .plaintext import generate_plaintext_subscription


def generate_base64_subscription(proxies: List[Proxy]) -> str:
    """Generate a Base64 subscription exactly equivalent to its URI list.

    Zero compatible nodes means empty plaintext and empty Base64; injecting a
    fake comment line makes clients misinterpret the subscription contents.
    """
    content = generate_plaintext_subscription(proxies)
    return base64.b64encode(content.encode("utf-8")).decode("utf-8")
