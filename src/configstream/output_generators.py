"""
Output Generators.
Refactored from output.py to reduce monolith size.
"""

import json
import base64
from typing import List, Dict, Any, Optional
from .models import Proxy
from .converters import to_clash_proxy, to_singbox_outbound

try:
    import yaml as yaml_lib
except ImportError:
    yaml_lib = None  # type: ignore


def generate_clash_config(proxies: List[Proxy]) -> str:
    """Generate Clash YAML configuration."""
    if yaml_lib is None:
        return "# PyYAML not installed"

    clash_proxies = []
    names = []

    for i, p in enumerate(proxies, 1):
        if not p.is_working:
            continue
        display_name = f"{p.country_code or 'XX'} {i:02d} | {p.protocol.upper()}"
        config = to_clash_proxy(p)
        if config:
            config["name"] = display_name
            clash_proxies.append(config)
            names.append(display_name)

    payload = {
        "port": 7890,
        "socks-port": 7891,
        "allow-lan": True,
        "mode": "Rule",
        "log-level": "info",
        "external-controller": "127.0.0.1:9090",
        "proxies": clash_proxies,
        "proxy-groups": [
            {
                "name": "🚀 ConfigStream Auto",
                "type": "url-test",
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
                "tolerance": 50,
                "proxies": names,
            },
            {
                "name": "🌍 Proxy Select",
                "type": "select",
                "proxies": names + ["🚀 ConfigStream Auto"],
            },
        ],
        "rules": ["MATCH,🚀 ConfigStream Auto"],
    }

    result = yaml_lib.dump(payload, allow_unicode=True, sort_keys=False)
    return str(result) if result else ""


def generate_singbox_config(proxies: List[Proxy]) -> str:
    """Legacy method for backward compatibility."""
    outbounds: List[Dict[str, Any]] = []
    selector_tags: List[str] = []

    for i, p in enumerate(proxies, 1):
        config = to_singbox_outbound(p)
        if config:
            tag = f"{p.country_code or 'XX'} {i:02d} | {p.protocol.upper()}"
            config["tag"] = tag
            outbounds.append(config)
            selector_tags.append(tag)

    if selector_tags:
        outbounds.insert(
            0,
            {
                "type": "selector",
                "tag": "🌍 Proxy Select",
                "outbounds": ["🚀 Auto"] + selector_tags,
            },
        )
        outbounds.insert(
            1,
            {
                "type": "urltest",
                "tag": "🚀 Auto",
                "outbounds": selector_tags,
                "url": "http://www.gstatic.com/generate_204",
                "interval": "5m",
            },
        )

    full_config = {
        "log": {"level": "info"},
        "inbounds": [
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "127.0.0.1",
                "listen_port": 2080,
            }
        ],
        "outbounds": outbounds,
    }

    return json.dumps(full_config, indent=2)


def generate_base64_subscription(proxies: List[Proxy]) -> str:
    """Generate standard Base64 subscription string."""
    lines = []
    for p in proxies:
        if p.config and p.protocol != "openvpn" and "://" in p.config:
            lines.append(p.config)
    text = "\n".join(lines)
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")
