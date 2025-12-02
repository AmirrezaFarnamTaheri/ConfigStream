import base64
from typing import List
from ..models import Proxy


def generate_base64_subscription(proxies: List[Proxy]) -> str:
    """Generates a base64 encoded subscription string."""
    lines = []
    for p in proxies:
        if p.config:
            lines.append(p.config)

    content = "\n".join(lines)
    return base64.b64encode(content.encode("utf-8")).decode("utf-8")
