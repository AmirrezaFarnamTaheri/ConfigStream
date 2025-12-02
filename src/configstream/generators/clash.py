import logging
from typing import List, Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

from ..models import Proxy
from ..converters import to_clash_proxy

logger = logging.getLogger(__name__)


def generate_clash_config(proxies: List[Proxy]) -> str:
    """Generates a Clash YAML configuration."""
    if not yaml:
        logger.warning("PyYAML not installed, skipping Clash generation")
        return ""

    proxies_list = []
    proxy_names = []

    for p in proxies:
        clash_proxy = to_clash_proxy(p)
        if clash_proxy:
            # Add name
            clash_proxy["name"] = p.remarks or f"Proxy-{p.id[:8]}"
            proxies_list.append(clash_proxy)
            proxy_names.append(clash_proxy["name"])

    config: dict[str, Any] = {
        "port": 7890,
        "socks-port": 7891,
        "allow-lan": True,
        "mode": "Rule",
        "log-level": "info",
        "external-controller": "127.0.0.1:9090",
        "proxies": proxies_list,
        "proxy-groups": [
            {
                "name": "FASTEST",
                "type": "url-test",
                "proxies": proxy_names,
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
            },
            {"name": "PROXY", "type": "select", "proxies": ["FASTEST"] + proxy_names},
        ],
        "rules": ["MATCH,PROXY"],
    }

    return yaml.dump(config, allow_unicode=True, sort_keys=False)
