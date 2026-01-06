# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from typing import List, Dict, Any, Optional, cast
from configstream.models import Proxy
from configstream.converters import to_singbox_outbound


class SingBoxGenerator:
    """
    Generates Sing-Box configuration (config.json) from a list of proxies.
    """

    def generate(
        self,
        proxies: List[Proxy],
        region: str = "all",
        extra_outbounds: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Creates a full Sing-Box config structure.
        """
        outbounds: List[Dict[str, Any]] = []

        # Legacy Tag Names
        SELECTOR_TAG = "🚀 Select Proxy"
        AUTO_TAG = "⚡ Best Latency"

        # Selector (Group)
        selector_outbound: Dict[str, Any] = {
            "type": "selector",
            "tag": SELECTOR_TAG,
            "outbounds": [AUTO_TAG, "DIRECT"],
            "interrupt_exist_connections": True,
        }

        # URLTest (Auto)
        urltest_outbound: Dict[str, Any] = {
            "type": "urltest",
            "tag": AUTO_TAG,
            "outbounds": [],
            "url": "http://www.gstatic.com/generate_204",
            "interval": "10m",
            "tolerance": 50,
        }

        # Add Extra Outbounds First (if any)
        if extra_outbounds:
            for extra in extra_outbounds:
                # Ensure extras are cleaned too if needed
                self._clean_outbound(extra)
                outbounds.append(extra)
                tag = extra.get("tag")

                # Logic for adding to selector:
                if tag:
                    otype = extra.get("type", "")
                    if otype == "wireguard":
                        # Mypy: cast outbounds to list
                        cast(List[str], selector_outbound["outbounds"]).append(tag)

        # Add Proxy Outbounds
        for p in proxies:
            try:
                # Use imported function directly
                outbound_config = to_singbox_outbound(p)

                # Check for None (Mypy)
                if outbound_config is None:
                    continue

                # Ensure tag exists if converter didn't provide it (Mock case)
                if "tag" not in outbound_config:
                    t = p.remarks or p.details.get("name") or f"proxy-{p.id}"
                    outbound_config["tag"] = t

                # Strip internal metadata
                self._clean_outbound(outbound_config)

                outbounds.append(outbound_config)
                tag = outbound_config.get("tag")

                if tag:
                    cast(List[str], selector_outbound["outbounds"]).append(tag)
                    cast(List[str], urltest_outbound["outbounds"]).append(tag)
            except Exception:
                continue

        # Assemble Final Config
        final_outbounds = [
            selector_outbound,
            urltest_outbound,
            *outbounds,
            {"type": "direct", "tag": "DIRECT"},
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
                    {"tag": "google", "address": "8.8.8.8", "detour": "DIRECT"},
                    {"tag": "local", "address": "local", "detour": "DIRECT"},
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
                    {"ip_is_private": True, "outbound": "DIRECT"},
                ],
                "auto_detect_interface": True,
            },
        }
        return config

    def _clean_outbound(self, outbound: Dict[str, Any]):
        keys_to_remove = [
            "_source",
            "_latency",
            "_country",
            "region",
            "origin_proxy",
            "_process",
        ]
        for k in keys_to_remove:
            outbound.pop(k, None)

        keys = list(outbound.keys())
        for k in keys:
            if k.startswith("_"):
                outbound.pop(k, None)


# [BACKWARD COMPATIBILITY]
def generate_singbox_config(
    proxies: List[Proxy],
    region: str = "all",
    extra_outbounds: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Wrapper for SingBoxGenerator.generate to maintain backward compatibility.
    """
    generator = SingBoxGenerator()
    config_dict = generator.generate(proxies, region, extra_outbounds)
    return json.dumps(config_dict, indent=2)


# [BACKWARD COMPATIBILITY TEST HELPER]
def _strip_internal_metadata(outbounds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Helper to match old test API.
    """
    gen = SingBoxGenerator()
    for o in outbounds:
        gen._clean_outbound(o)
    return outbounds
