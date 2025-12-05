from typing import List
import logging
import yaml  # type: ignore

from ..models import Proxy

# Note: Clash converter might need implementation or stub if missing
# Assuming we have a stub or basic converter
from ..converters.clash import to_clash_proxy

logger = logging.getLogger(__name__)


def generate_clash_config(proxies: List[Proxy]) -> str:
    """
    Generates a Clash configuration YAML string.
    Does NOT currently support complex chains (extra_outbounds) as per audit.
    """
    clash_proxies = []
    proxy_names = []

    for p in proxies:
        if not p.is_working:
            continue

        c_proxy = to_clash_proxy(p)
        if c_proxy:
            clash_proxies.append(c_proxy)
            proxy_names.append(c_proxy["name"])

    config = {
        "port": 7890,
        "socks-port": 7891,
        "allow-lan": True,
        "mode": "Rule",
        "log-level": "info",
        "proxies": clash_proxies,
        "proxy-groups": [
            {
                "name": "🚀 Select Proxy",
                "type": "select",
                "proxies": ["⚡ Best Latency", "DIRECT"] + proxy_names,
            },
            {
                "name": "⚡ Best Latency",
                "type": "url-test",
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
                "proxies": proxy_names,
            },
        ],
        "rules": ["MATCH,🚀 Select Proxy"],
    }

    return str(yaml.dump(config, allow_unicode=True, sort_keys=False))
