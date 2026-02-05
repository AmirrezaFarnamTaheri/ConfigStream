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

        added_tags: set[str] = set()

        def _append_outbound(
            outbound: Dict[str, Any], *, add_to_selector: bool
        ) -> bool:
            self._clean_outbound(outbound)
            tag = outbound.get("tag")
            if tag and tag in added_tags:
                return False
            outbounds.append(outbound)
            if tag:
                added_tags.add(tag)
                if add_to_selector:
                    cast(List[str], selector_outbound["outbounds"]).append(tag)
            return True

        # Add Extra Outbounds First (if any)
        if extra_outbounds:
            for extra in extra_outbounds:
                otype = extra.get("type", "")
                _append_outbound(extra, add_to_selector=otype == "wireguard")

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

                extra_chain = outbound_config.pop("_extra_outbounds", None)
                if isinstance(extra_chain, list):
                    for extra in extra_chain:
                        if isinstance(extra, dict):
                            _append_outbound(extra, add_to_selector=False)

                # Strip internal metadata
                self._clean_outbound(outbound_config)

                added = _append_outbound(outbound_config, add_to_selector=True)
                tag = outbound_config.get("tag")
                if added and tag:
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

        # Build DNS profile with FakeIP support
        dns_servers = [
            {"tag": "remote", "address": "https://8.8.8.8/dns-query", "detour": SELECTOR_TAG},
            {"tag": "local", "address": "local", "detour": "DIRECT"},
        ]
        
        # Add FakeIP server for DNS-poisoning resistance
        dns_servers.append({"tag": "fakeip", "address": "fakeip"})
        
        dns_rules = [
            {"outbound": "any", "server": "remote"},
            {"query_type": ["A", "AAAA"], "server": "fakeip", "rewrite_ttl": 1},
        ]
        
        dns_config = {
            "servers": dns_servers,
            "rules": dns_rules,
            "fakeip": {
                "enabled": True,
                "inet4_range": "198.18.0.0/15",
                "inet6_range": "fc00::/18",
            },
        }

        config = {
            "log": {
                "level": "info",
                "timestamp": True,
            },
            "dns": dns_config,
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
                "rules": self._build_route_rules(SELECTOR_TAG),
                "auto_detect_interface": True,
            },
        }
        return config

    def _build_route_rules(self, selector_tag: str) -> List[Dict[str, Any]]:
        """Build route rules with optional geosite/geoip support."""
        rules = [
            {"protocol": "dns", "outbound": "dns-out"},
            {"ip_is_private": True, "outbound": "DIRECT"},
        ]
        
        # Check if geosite.db and geoip.db are available
        from pathlib import Path
        from configstream.config import AppSettings
        
        settings = AppSettings()
        data_dir = Path(settings.GEOIP_CITY_DB_PATH).parent if hasattr(settings, 'GEOIP_CITY_DB_PATH') else Path("data")
        singbox_data_dir = data_dir / "singbox"
        geosite_path = singbox_data_dir / "geosite.db"
        geoip_path = singbox_data_dir / "geoip.db"
        
        # Add geosite/geoip rules if databases are available
        if geosite_path.exists() and geoip_path.exists():
            # Domestic bypass for .ir domains and Iran IPs
            rules.append({
                "geosite": ["ir", "category-ir"],
                "geoip": ["ir", "private"],
                "outbound": "DIRECT",
            })
            # Force blocked sites through proxy
            rules.append({
                "geosite": ["google", "telegram", "twitter", "youtube", "meta"],
                "outbound": selector_tag,
            })
        else:
            # Log debug message if databases are missing
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(
                "geosite.db or geoip.db not found. Run 'configstream update-databases' to enable advanced routing rules."
            )
        
        return rules

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
    return json.dumps(config_dict, indent=2, ensure_ascii=False)


# [BACKWARD COMPATIBILITY TEST HELPER]
def _strip_internal_metadata(outbounds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Helper to match old test API.
    """
    gen = SingBoxGenerator()
    for o in outbounds:
        gen._clean_outbound(o)
    return outbounds
