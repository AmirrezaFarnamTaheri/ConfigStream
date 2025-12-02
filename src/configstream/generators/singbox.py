import json
import logging
from typing import List, Any

from ..models import Proxy
from ..converters import to_singbox_outbound

logger = logging.getLogger(__name__)

def generate_singbox_config(proxies: List[Proxy]) -> str:
    """Generates a Sing-box JSON configuration (The Sniper/The Tank)."""
    outbounds = []
    selector_tags = []

    # 1. Convert proxies
    for p in proxies:
        sb_proxy = to_singbox_outbound(p)
        if sb_proxy:
            # Use 'tag' for reference
            tag = p.remarks or f"{p.protocol}-{p.id[:8]}"
            sb_proxy["tag"] = tag
            outbounds.append(sb_proxy)
            selector_tags.append(tag)

    # 2. Add Selectors/URLTest
    if selector_tags:
        # URL Test (Best Latency)
        outbounds.append({
            "type": "urltest",
            "tag": "⚡ Best Latency",
            "outbounds": selector_tags,
            "url": "http://cp.cloudflare.com/generate_204",
            "interval": "10m"
        })

        # Selector
        outbounds.append({
            "type": "selector",
            "tag": "🚀 Select Proxy",
            "outbounds": ["⚡ Best Latency"] + selector_tags,
            "default": "⚡ Best Latency"
        })

    config: dict[str, Any] = {
        "log": {
            "level": "info",
            "timestamp": True
        },
        "inbounds": [
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "127.0.0.1",
                "listen_port": 2080
            }
        ],
        "outbounds": outbounds
    }

    return json.dumps(config, indent=2)
