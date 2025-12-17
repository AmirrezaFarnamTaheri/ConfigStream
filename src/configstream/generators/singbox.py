import json
import logging
from typing import List, Any, Optional

from ..models import Proxy
from ..converters import to_singbox_outbound

logger = logging.getLogger(__name__)


def generate_singbox_config(
    proxies: List[Proxy], extra_outbounds: Optional[List[dict[str, Any]]] = None
) -> str:
    """Generates a Sing-box JSON configuration (The Sniper/The Tank)."""
    outbounds = []
    selector_tags = []

    # 1. Convert proxies with unique tags
    seen_tags = set()
    for p in proxies:
        sb_proxy = to_singbox_outbound(p)
        if sb_proxy:
            # Enforce globally unique outbound tags
            # Include hash of (protocol, host, port) or use ID which is stable hash
            base_tag = p.remarks or f"{p.protocol}-{p.id[:8]}"
            tag = base_tag
            counter = 1
            while tag in seen_tags:
                tag = f"{base_tag}-{counter}"
                counter += 1

            seen_tags.add(tag)
            sb_proxy["tag"] = tag
            outbounds.append(sb_proxy)
            selector_tags.append(tag)

    # 2. Append Extra Outbounds (e.g. Washed Chains)
    if extra_outbounds:
        for out in extra_outbounds:
            # Check if this outbound is meant to be user-selectable
            # Washed chains usually have a WireGuard outbound with tag "🛡️ Secure-..."
            # The Relay outbound is "RELAY-..." and should not be in the selector directly,
            # as it is only a detour for the WireGuard one.
            outbounds.append(out)
            tag = out.get("tag", "")
            if tag and not tag.startswith("RELAY-"):
                selector_tags.append(tag)

    # 3. Add Selectors/URLTest
    if selector_tags:
        # URL Test (Best Latency)
        outbounds.append(
            {
                "type": "urltest",
                "tag": "⚡ Best Latency",
                "outbounds": selector_tags,
                "url": "http://cp.cloudflare.com/generate_204",
                "interval": "10m",
            }
        )

        # Selector
        outbounds.append(
            {
                "type": "selector",
                "tag": "🚀 Select Proxy",
                "outbounds": ["⚡ Best Latency"] + selector_tags,
                "default": "⚡ Best Latency",
            }
        )

    # Add explicit route section
    route = {
        "rules": [
            {"protocol": "dns", "outbound": "dns-out"},
            {"clash_mode": "Direct", "outbound": "DIRECT"},
            {"clash_mode": "Global", "outbound": "🚀 Select Proxy"},
        ],
        "final": "🚀 Select Proxy",
        "auto_detect_interface": True,
    }

    # Ensure DIRECT and dns-out exist
    if not any(o["tag"] == "DIRECT" for o in outbounds):
        outbounds.append({"type": "direct", "tag": "DIRECT"})
    if not any(o["tag"] == "dns-out" for o in outbounds):
        outbounds.append({"type": "dns", "tag": "dns-out"})

    config: dict[str, Any] = {
        "log": {"level": "info", "timestamp": True},
        "inbounds": [
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "127.0.0.1",
                "listen_port": 2080,
            }
        ],
        "outbounds": outbounds,
        "route": route,
    }

    return json.dumps(config, indent=2)
