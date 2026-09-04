# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import copy
import json
from typing import List, Dict, Any, Optional, cast
from configstream.models import Proxy
from configstream.converters import to_singbox_outbound


class SingBoxGenerator:
    """
    Generates Sing-Box configuration (config.json) from a list of proxies.
    Updated to match chaiin-example-format/e1.json structure.
    """

    def generate(
        self,
        proxies: List[Proxy],
        region: str = "all",
        extra_outbounds: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Creates a full Sing-Box config structure aligned with V2RayN/Sing-box best practices.
        """
        outbounds: List[Dict[str, Any]] = []

        # Selector/Auto tag names (used by sing-box UI clients)
        SELECTOR_TAG = "🌍 Proxy Select"
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
        tag_remap: Dict[str, str] = {}  # old_tag -> new_tag when uniquified

        def _uniquify_tag(tag: str) -> str:
            if not tag or tag not in added_tags:
                return tag
            suffix = 0
            while f"{tag}-{suffix}" in added_tags:
                suffix += 1
            return f"{tag}-{suffix}"

        def _append_outbound(
            outbound: Dict[str, Any], *, add_to_selector: bool
        ) -> Optional[str]:
            self._clean_outbound(outbound)
            # Resolve detour if target was uniquified
            detour = outbound.get("detour")
            tag = outbound.get("tag")
            needs_copy = False
            if isinstance(detour, str) and detour in tag_remap:
                needs_copy = True
            if tag and tag in added_tags:
                needs_copy = True
            if needs_copy:
                outbound = copy.deepcopy(outbound)
                if (
                    isinstance(outbound.get("detour"), str)
                    and outbound["detour"] in tag_remap
                ):
                    outbound["detour"] = tag_remap[outbound["detour"]]
                if outbound.get("tag") and outbound["tag"] in added_tags:
                    new_tag = _uniquify_tag(outbound["tag"])
                    tag_remap[outbound["tag"]] = new_tag
                    tag = new_tag
                    outbound["tag"] = tag
            outbounds.append(outbound)
            if tag:
                added_tags.add(tag)
                if add_to_selector:
                    cast(List[str], selector_outbound["outbounds"]).append(tag)
            # Return the final (possibly uniquified) tag so callers reference the
            # tag actually written, not the stale pre-uniquification value.
            return tag

        # Add Extra Outbounds First (if any)
        # Build a set of tags referenced as detour targets (inner hops)
        # so we can identify entry-point outbounds vs inner relay hops.
        _detour_targets: set[str] = set()
        if extra_outbounds:
            for _eo in extra_outbounds:
                _dt = _eo.get("detour")
                if isinstance(_dt, str) and _dt:
                    _detour_targets.add(_dt)

        if extra_outbounds:
            for extra in extra_outbounds:
                tag = extra.get("tag", "")
                # Entry point: has detour (chains through inner hop),
                # OR is not referenced as anyone else's detour target
                # (standalone outbound like a wireguard endpoint).
                # Inner hop: referenced as another outbound's detour target
                # and does NOT itself chain further — should NOT be selectable.
                is_inner_hop = bool(tag and tag in _detour_targets)
                is_entry_point = not is_inner_hop
                final_tag = _append_outbound(extra, add_to_selector=is_entry_point)
                if is_entry_point and final_tag:
                    cast(List[str], urltest_outbound["outbounds"]).append(final_tag)

        # Add Proxy Outbounds
        for p in proxies:
            try:
                # Use imported function directly
                outbound_config = to_singbox_outbound(p)

                # Check for None (Mypy)
                if outbound_config is None:
                    continue

                # Ensure tag exists if converter didn't provide it
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

                final_tag = _append_outbound(outbound_config, add_to_selector=True)
                if final_tag:
                    cast(List[str], urltest_outbound["outbounds"]).append(final_tag)
            except Exception:  # nosec B112
                logging.getLogger(__name__).debug("Suppressed broad exception")
                continue

        # Empty urltest groups fail both native `sing-box check` and the
        # Pages contract. Country/protocol subsets can have no convertible
        # outbounds; fall back to direct so the config remains valid.
        urltest_members = cast(List[str], urltest_outbound["outbounds"])
        if not urltest_members:
            urltest_members.append("direct")

        # Assemble Final Config
        final_outbounds = [
            selector_outbound,
            urltest_outbound,
            *outbounds,
            {"type": "direct", "tag": "direct"},
            {"type": "block", "tag": "block"},
            {"type": "dns", "tag": "dns-out"},
        ]

        from configstream.dns_profiles import build_singbox_dns_profile

        # Emit the 1.12+ typed DNS model directly instead of depending on the
        # release finalizer to migrate legacy address/address_resolver fields.
        dns_config = build_singbox_dns_profile()

        # Inbounds matched to e1.json
        inbounds = [
            {
                "type": "mixed",
                "tag": "socks",
                "listen": "127.0.0.1",
                "listen_port": 10808,
            }
        ]

        # Route — compatible format for v2rayN / NekoRay / Hiddify
        route = {
            # Hostname-based proxy/chain outbounds inherit this resolver. This
            # is required by Sing-box 1.12+ and fixes native checks for chain
            # artifacts whose upstream server is a domain name.
            "default_domain_resolver": "local_local",
            "rules": [
                {"action": "sniff"},
                {"protocol": ["dns"], "action": "hijack-dns"},
                {"outbound": "direct", "clash_mode": "Direct"},
                {"outbound": SELECTOR_TAG, "clash_mode": "Global"},
                {"network": ["udp"], "port": [443], "action": "reject"},
                {"outbound": "direct", "protocol": ["bittorrent"]},
                {"rule_set": ["geosite-category-ads-all"], "action": "reject"},
                {"outbound": "direct", "ip_is_private": True},
                {
                    "outbound": "direct",
                    "rule_set": ["geosite-private", "geosite-ir", "geoip-ir"],
                },
                {"outbound": SELECTOR_TAG, "port_range": ["0:65535"]},
            ],
            "rule_set": [
                {
                    "tag": "geosite-category-ads-all",
                    "type": "remote",
                    "format": "binary",
                    "url": "https://github.com/SagerNet/sing-geosite/raw/rule-set/geosite-category-ads-all.srs",
                    "download_detour": SELECTOR_TAG,
                },
                {
                    "tag": "geosite-private",
                    "type": "remote",
                    "format": "binary",
                    "url": "https://github.com/SagerNet/sing-geosite/raw/rule-set/geosite-private.srs",
                    "download_detour": SELECTOR_TAG,
                },
                {
                    "tag": "geosite-ir",
                    "type": "remote",
                    "format": "binary",
                    "url": "https://github.com/SagerNet/sing-geosite/raw/rule-set/geosite-ir.srs",
                    "download_detour": SELECTOR_TAG,
                },
                {
                    "tag": "geoip-ir",
                    "type": "remote",
                    "format": "binary",
                    "url": "https://github.com/SagerNet/sing-geoip/raw/rule-set/geoip-ir.srs",
                    "download_detour": SELECTOR_TAG,
                },
            ],
            "final": SELECTOR_TAG,
        }

        # Experimental matched to e1.json
        experimental = {
            "cache_file": {"enabled": True, "path": "cache.db", "store_fakeip": False},
            "clash_api": {"external_controller": "127.0.0.1:10813"},
        }

        config = {
            "log": {
                "level": "warn",
                "timestamp": True,
            },
            "dns": dns_config,
            "inbounds": inbounds,
            "outbounds": final_outbounds,
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


def generate_singbox_config(
    proxies: List[Proxy],
    region: str = "all",
    extra_outbounds: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Generate a complete Sing-box JSON config string from proxies."""
    generator = SingBoxGenerator()
    config_dict = generator.generate(proxies, region, extra_outbounds)
    return json.dumps(config_dict, indent=2, ensure_ascii=False)


def _strip_internal_metadata(outbounds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove internal metadata fields from outbound dicts."""
    gen = SingBoxGenerator()
    for o in outbounds:
        gen._clean_outbound(o)
    return outbounds
