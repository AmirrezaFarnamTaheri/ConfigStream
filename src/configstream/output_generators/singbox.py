from typing import List, Dict, Any, Optional
import json
import logging

from ..models import Proxy
from ..converters.singbox import to_singbox_outbound

logger = logging.getLogger(__name__)


def generate_singbox_config(
    proxies: List[Proxy], extra_outbounds: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Generates a complete Sing-box configuration JSON object.
    Supports extra_outbounds for chains/washing.
    """
    outbounds = []

    # Standard Selectors
    # IMPORTANT: We add a 'tag' field to selectors so they can be identified in the final list
    selectors = {
        "🚀 Select Proxy": {
            "type": "selector",
            "tag": "🚀 Select Proxy",
            "outbounds": ["⚡ Best Latency", "DIRECT"],
            "interrupt_exist_connections": True,
        },
        "⚡ Best Latency": {
            "type": "urltest",
            "tag": "⚡ Best Latency",
            "outbounds": [],
            "url": "https://www.gstatic.com/generate_204",
            "interval": "10m",
            "tolerance": 50,
        },
        "DIRECT": {"type": "direct", "tag": "DIRECT"},
    }

    # 1. Process Standard Proxies
    for p in proxies:
        if not p.is_working:
            continue

        out = to_singbox_outbound(p)
        if out:
            outbounds.append(out)
            tag = out.get("tag")  # Use .get() to avoid KeyError
            if tag:
                selectors["🚀 Select Proxy"]["outbounds"].append(tag)
                selectors["⚡ Best Latency"]["outbounds"].append(tag)

    # 2. Process Extra Outbounds (Chains/Washed)
    if extra_outbounds:
        for out in extra_outbounds:
            outbounds.append(out)
            tag = out.get("tag")

            if tag:
                # Filter Relays from UI
                if not tag.startswith("RELAY-"):
                    selectors["🚀 Select Proxy"]["outbounds"].append(tag)
                    selectors["⚡ Best Latency"]["outbounds"].append(tag)

    # 3. Assemble Final Config
    final_outbounds = [
        selectors["🚀 Select Proxy"],
        selectors["⚡ Best Latency"],
        selectors["DIRECT"],
    ] + outbounds

    return {
        "log": {"level": "info", "timestamp": True},
        "dns": {
            "servers": [
                {"tag": "google", "address": "8.8.8.8", "detour": "DIRECT"},
                {"tag": "local", "address": "local", "detour": "DIRECT"},
            ],
            "rules": [{"outbound": "any", "server": "google"}],
        },
        "inbounds": [
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "127.0.0.1",
                "listen_port": 2080,
            }
        ],
        "outbounds": final_outbounds,
        "route": {
            "rules": [
                {"protocol": "dns", "outbound": "dns-out"},
                {"ip_is_private": True, "outbound": "DIRECT"},
                {"clash_mode": "Direct", "outbound": "DIRECT"},
                {"clash_mode": "Global", "outbound": "🚀 Select Proxy"},
            ],
            "auto_detect_interface": True,
        },
    }
