# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from typing import List, Dict, Any, Optional, cast
from configstream.models import Proxy
from configstream.converters import to_singbox_outbound


class SingBoxGenerator:
    """
    Generates Sing-Box configuration (config.json) from a list of proxies.
    Adopts format from chaiin-example-format/e1.json.
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
            "outbounds": [AUTO_TAG, "direct"],
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
                outbound_config = to_singbox_outbound(p)
                if outbound_config is None:
                    continue

                if "tag" not in outbound_config:
                    t = p.remarks or p.details.get("name") or f"proxy-{p.id}"
                    outbound_config["tag"] = t

                extra_chain = outbound_config.pop("_extra_outbounds", None)
                if isinstance(extra_chain, list):
                    for extra in extra_chain:
                        if isinstance(extra, dict):
                            _append_outbound(extra, add_to_selector=False)

                self._clean_outbound(outbound_config)

                # Check if this is a chain ending (e.g. valid proxy)
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
            {"type": "direct", "tag": "direct"},
            {"type": "block", "tag": "block"},
            {"type": "dns", "tag": "dns-out"},
        ]

        # DNS Configuration matching e1.json
        dns_config = {
            "servers": [
                {"server": "223.5.5.5", "type": "udp", "tag": "local_local"},
                {
                    "server": "cloudflare-dns.com",
                    "domain_resolver": "hosts_dns",
                    "path": "/dns-query",
                    "type": "https",
                    "tag": "remote_dns",
                    "detour": SELECTOR_TAG,
                },
                {
                    "server": "dns.alidns.com",
                    "domain_resolver": "hosts_dns",
                    "path": "/dns-query",
                    "type": "https",
                    "tag": "direct_dns",
                },
                {
                    "predefined": {
                        "dns.google": ["8.8.8.8", "8.8.4.4", "2001:4860:4860::8888", "2001:4860:4860::8844"],
                        "dns.alidns.com": ["223.5.5.5", "223.6.6.6", "2400:3200::1", "2400:3200:baba::1"],
                        "one.one.one.one": ["1.1.1.1", "1.0.0.1", "2606:4700:4700::1111", "2606:4700:4700::1001"],
                        "1dot1dot1dot1.cloudflare-dns.com": ["1.1.1.1", "1.0.0.1", "2606:4700:4700::1111", "2606:4700:4700::1001"],
                        "cloudflare-dns.com": ["104.16.249.249", "104.16.248.249", "2606:4700::6810:f8f9", "2606:4700::6810:f9f9"],
                    },
                    "type": "hosts",
                    "tag": "hosts_dns",
                },
            ],
            "rules": [
                {"server": "local_local", "domain": ["sing_box-ProxyChain"]},
                {"server": "hosts_dns", "ip_accept_any": True},
                {"server": "remote_dns", "clash_mode": "Global"},
                {"server": "direct_dns", "clash_mode": "Direct"},
                {"action": "predefined", "rcode": "NOTIMP", "query_type": [64, 65]},
                {"rule_set": ["geosite-category-ads-all"], "action": "predefined", "rcode": "NXDOMAIN"},
                {"server": "direct_dns", "rule_set": ["geosite-private", "geosite-ir"]},
            ],
            "final": "remote_dns",
            "independent_cache": True,
        }

        # Experimental Section
        experimental = {
            "cache_file": {
                "enabled": True,
                "path": "cache.db",
                "store_fakeip": False,
            },
            "clash_api": {
                "external_controller": "127.0.0.1:10813"
            }
        }

        # Route Rules
        route = {
            "default_domain_resolver": {
                "server": "direct_dns",
                "strategy": ""
            },
            "rules": [
                {"action": "sniff"},
                {"protocol": ["dns"], "action": "hijack-dns"},
                {"outbound": "direct", "clash_mode": "Direct"},
                {"outbound": SELECTOR_TAG, "clash_mode": "Global"},
                {"outbound": "direct", "ip_cidr": ["8.8.8.8"]},
                {"network": ["udp"], "port": [443], "action": "reject"},
                {"outbound": "direct", "protocol": ["bittorrent"]},
                {"rule_set": ["geosite-category-ads-all"], "action": "reject"},
                {"outbound": "direct", "ip_is_private": True},
                {"outbound": "direct", "rule_set": ["geosite-private", "geosite-ir", "geoip-ir"]},
                {"outbound": SELECTOR_TAG, "port_range": ["0:65535"]},
            ],
            "rule_set": [
                {"tag": "geosite-category-ads-all", "type": "remote", "format": "binary", "url": "https://raw.githubusercontent.com/SagerNet/sing-geosite/rule-set/geosite-category-ads-all.srs", "download_detour": SELECTOR_TAG},
                {"tag": "geosite-private", "type": "remote", "format": "binary", "url": "https://raw.githubusercontent.com/SagerNet/sing-geosite/rule-set/geosite-private.srs", "download_detour": SELECTOR_TAG},
                {"tag": "geosite-ir", "type": "remote", "format": "binary", "url": "https://github.com/chocolate4u/Iran-sing-box-rules/releases/latest/download/geosite-ir.srs", "download_detour": SELECTOR_TAG},
                {"tag": "geoip-ir", "type": "remote", "format": "binary", "url": "https://github.com/chocolate4u/Iran-sing-box-rules/releases/latest/download/geoip-ir.srs", "download_detour": SELECTOR_TAG},
            ],
            "final": SELECTOR_TAG
        }

        config = {
            "log": {
                "level": "warn",
                "timestamp": True,
            },
            "dns": dns_config,
            "inbounds": [
                {
                    "type": "mixed",
                    "tag": "socks",
                    "listen": "127.0.0.1",
                    "listen_port": 10808,
                }
            ],
            "outbounds": final_outbounds,
            "endpoints": [],
            "route": route,
            "experimental": experimental,
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
