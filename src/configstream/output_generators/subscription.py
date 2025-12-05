from typing import List, Dict, Any
import base64
import logging

from ..models import Proxy
from ..converters.common import to_uri

logger = logging.getLogger(__name__)


def generate_subscription_file(proxies: List[Proxy]) -> str:
    """
    Generates a Base64-encoded subscription file content.
    Contains standard URI schemes (vless://, vmess://, etc.)
    """
    lines = []
    for p in proxies:
        if not p.is_working:
            continue

        uri = to_uri(p)
        if uri:
            # Append name/remarks if possible (standard is URI#Name)
            # to_uri handles basic construction
            lines.append(uri)

    content = "\n".join(lines)
    return base64.b64encode(content.encode("utf-8")).decode("utf-8")
