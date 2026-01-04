# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from typing import List, Dict, Any
from configstream.models import Proxy
from configstream.converters import to_singbox_outbound


class SingBoxGenerator:
    """
    Generates Sing-Box configuration (config.json) from a list of proxies.
    """

    def generate(self, proxies: List[Proxy], region: str = "all") -> Dict[str, Any]:
        """
        Creates a full Sing-Box config structure.
        """
        outbounds = []

        # Selector (Group)
        selector_outbound = {
            "type": "selector",
            "tag": "select",
            "outbounds": ["auto", "direct"],
            "interrupt_exist_connections": True,
        }

        # URLTest (Auto)
        urltest_outbound = {
            "type": "urltest",
            "tag": "auto",
            "outbounds": [],
            "url": "http://www.gstatic.com/generate_204",
            "interval": "10m",
            "tolerance": 50,
        }

        # Add Proxy Outbounds
        for p in proxies:
            try:
                # Use imported function directly
                outbound_config = to_singbox_outbound(p)

                # [FIX] Strip internal metadata
                self._clean_outbound(outbound_config)

                outbounds.append(outbound_config)
                tag = outbound_config["tag"]

                selector_outbound["outbounds"].append(tag)
                urltest_outbound["outbounds"].append(tag)
            except Exception:
                continue

        # Assemble Final Config
        final_outbounds = [
            selector_outbound,
            urltest_outbound,
            *outbounds,
            {"type": "direct", "tag": "direct"},
            {"type": "dns", "tag": "dns-out"},
            {"type": "block", "tag": "block"},
        ]

        config = {
            "log": {
                "level": "info",
                "timestamp": True,
            },
            "dns": {
                "servers": [
                    {"tag": "google", "address": "8.8.8.8", "detour": "direct"},
                    {"tag": "local", "address": "local", "detour": "direct"},
                ],
                "rules": [
                    {"outbound": "any", "server": "google"},
                ],
            },
            "inbounds": [
                {
                    "type": "mixed",
                    "tag": "mixed-in",
                    "listen": "0.0.0.0",
                    "listen_port": 2080,
                    "sniff": True,
                }
            ],
            "outbounds": final_outbounds,
            "route": {
                "rules": [
                    {"protocol": "dns", "outbound": "dns-out"},
                    {"ip_is_private": True, "outbound": "direct"},
                ],
                "auto_detect_interface": True,
            },
        }
        return config

    def _clean_outbound(self, outbound: dict):
        keys_to_remove = ["_source", "_latency", "_country", "region", "origin_proxy"]
        for k in keys_to_remove:
            outbound.pop(k, None)

# [BACKWARD COMPATIBILITY]
def generate_singbox_config(proxies: List[Proxy], region: str = "all") -> Dict[str, Any]:
    """
    Wrapper for SingBoxGenerator.generate to maintain backward compatibility.
    """
    generator = SingBoxGenerator()
    return generator.generate(proxies, region)

# [ADDITIONAL COMPATIBILITY]
# If the caller expected ProxyConverter class, we can mock it here or
# fix the caller. The traceback showed `from configstream.converters import ProxyConverter` FAILED
# inside `singbox.py` (which I just edited).
# Wait, I previously wrote `from configstream.converters import ProxyConverter` in `singbox.py`.
# But `configstream.converters` does NOT export `ProxyConverter`.
# So I should change `singbox.py` to use `to_singbox_outbound`.
