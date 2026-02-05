# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
from typing import List, Any, Optional, Dict

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore

from ..models import Proxy
from ..converters import to_clash_proxy

logger = logging.getLogger(__name__)


def generate_clash_config(
    proxies: List[Proxy],
    extra_outbounds: Any = None,
    dns_profile: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generates a Clash YAML configuration.

    [FIX] Added `extra_outbounds` argument to prevent crash when pipeline passes it.
    However, Clash generator currently only supports standard proxies.
    Future work: Convert Sing-box chains to Clash relay groups.
    """
    if not yaml:
        logger.warning("PyYAML not installed, skipping Clash generation")
        return ""

    proxies_list = []
    proxy_names = []
    seen_names: set[str] = set()  # Track used names to prevent duplicates

    for p in proxies:
        clash_proxy = to_clash_proxy(p)
        if clash_proxy:
            # Generate unique name - avoid tag collisions
            base_name = p.remarks or f"Proxy-{p.id[:8]}"
            unique_name = base_name
            counter = 1
            while unique_name in seen_names:
                unique_name = f"{base_name}-{counter}"
                counter += 1
            seen_names.add(unique_name)
            clash_proxy["name"] = unique_name
            proxies_list.append(clash_proxy)
            proxy_names.append(clash_proxy["name"])

    # Guard against empty proxy groups which creates invalid Clash config
    if not proxy_names:
        logger.warning("No valid proxies for Clash config generation")
        return ""

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

    if dns_profile:
        config["dns"] = dns_profile

    return str(yaml.dump(config, allow_unicode=True, sort_keys=False))
