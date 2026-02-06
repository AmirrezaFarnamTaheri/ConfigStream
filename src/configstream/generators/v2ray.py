# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import logging
from typing import List, Any, Dict, Optional

from ..models import Proxy

logger = logging.getLogger(__name__)


class V2RayGenerator:
    """
    Generates V2Ray/Xray JSON configuration files.
    Supports standard protocols (VMess, VLESS, Trojan, Shadowsocks) and chaining via 'dialerProxy'.
    """

    def generate(
        self,
        proxies: List[Proxy],
        region: str = "all",
        extra_outbounds: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a full V2Ray JSON configuration.
        """
        # Base Configuration matching e2.json structure
        config = {
            "log": {
                "loglevel": "warning"
            },
            "dns": {
                "hosts": {
                    "geosite:category-ads-all": ["127.0.0.1"],
                    "domain:googleapis.cn": ["googleapis.com"],
                },
                "servers": [
                    "1.1.1.1",
                    "8.8.8.8",
                    {
                        "address": "8.8.8.8",
                        "domains": ["geosite:ir"],
                        "expectIPs": ["geoip:ir"]
                    }
                ]
            },
            "inbounds": [
                {
                    "tag": "socks",
                    "port": 10808,
                    "listen": "127.0.0.1",
                    "protocol": "socks",
                    "sniffing": {
                        "enabled": True,
                        "destOverride": ["http", "tls"]
                    },
                    "settings": {
                        "auth": "noauth",
                        "udp": True,
                        "allowTransparent": False
                    }
                },
                {
                    "tag": "http",
                    "port": 10809,
                    "listen": "127.0.0.1",
                    "protocol": "http",
                    "settings": {
                        "userLevel": 0
                    }
                }
            ],
            "outbounds": [],
            "routing": {
                "domainStrategy": "IPOnDemand",
                "rules": [
                    {
                        "type": "field",
                        "outboundTag": "direct",
                        "ip": ["geoip:private", "geoip:ir"]
                    },
                    {
                        "type": "field",
                        "outboundTag": "direct",
                        "domain": ["geosite:private", "geosite:ir"]
                    },
                    {
                        "type": "field",
                        "outboundTag": "block",
                        "domain": ["geosite:category-ads-all"]
                    }
                ]
            },
            "policy": {
                "system": {
                    "statsOutboundUplink": True,
                    "statsOutboundDownlink": True
                }
            }
        }

        # Generate Outbounds
        outbounds = []

        # 1. Add Proxies
        for i, proxy in enumerate(proxies):
            outbound = self._convert_proxy(proxy, index=i)
            if outbound:
                outbounds.append(outbound)
                # If this proxy is a chain (handled in conversion), we might need to add the underlying proxy too.
                # But for now, let's assume _convert_proxy handles the main outbound.
                # Real chaining usually requires the 'next' proxy to be in the outbounds list too.
                # This implementation assumes simple proxies or that the caller provides the chain components.

        # 2. Add Extra Outbounds (if any)
        if extra_outbounds:
            outbounds.extend(extra_outbounds)

        # 3. Add Default Outbounds (Direct, Block)
        outbounds.append({
            "tag": "direct",
            "protocol": "freedom",
            "settings": {}
        })
        outbounds.append({
            "tag": "block",
            "protocol": "blackhole",
            "settings": {}
        })

        config["outbounds"] = outbounds
        return config

    def _convert_proxy(self, proxy: Proxy, index: int) -> Optional[Dict[str, Any]]:
        """
        Convert a ConfigStream Proxy object to a V2Ray outbound dictionary.
        """
        # Determine tag
        tag = proxy.remarks or f"proxy-{index}"

        details = proxy.details or {}

        # Common Stream Settings
        stream_settings = {
            "network": "tcp",
            "security": "none",
        }

        # Transport - FIXED: Access via details, fallback to None
        network = details.get("type") or details.get("network") or details.get("transport")
        if network:
             stream_settings["network"] = network

        # TLS
        security = details.get("security") or details.get("tls")
        if security == "tls" or security == "reality":
             stream_settings["security"] = security
             stream_settings["tlsSettings"] = {
                 "serverName": proxy.sni or "",
                 "allowInsecure": details.get("allowInsecure", False)
             }
             if security == "reality":
                 stream_settings["realitySettings"] = {
                     "serverName": proxy.sni or "",
                     "publicKey": details.get("pbk") or details.get("publicKey") or "",
                     "shortId": details.get("sid") or details.get("shortId") or ""
                 }

        # Protocol Specific Settings
        settings = {}

        if proxy.protocol == "vmess":
            settings = {
                "vnext": [{
                    "address": proxy.address,
                    "port": proxy.port,
                    "users": [{
                        "id": proxy.uuid,
                        "alterId": int(details.get("alterId", 0)),
                        "security": details.get("cipher", "auto")
                    }]
                }]
            }
        elif proxy.protocol == "vless":
            settings = {
                "vnext": [{
                    "address": proxy.address,
                    "port": proxy.port,
                    "users": [{
                        "id": proxy.uuid,
                        "encryption": details.get("encryption", "none")
                    }]
                }]
            }
            if details.get("flow"):
                settings["vnext"][0]["users"][0]["flow"] = details["flow"]

        elif proxy.protocol == "trojan":
            settings = {
                "servers": [{
                    "address": proxy.address,
                    "port": proxy.port,
                    "password": details.get("password") or proxy.uuid
                }]
            }

        elif proxy.protocol == "shadowsocks":
             settings = {
                "servers": [{
                    "address": proxy.address,
                    "port": proxy.port,
                    "method": details.get("method", "chacha20-ietf-poly1305"),
                    "password": details.get("password") or proxy.uuid
                }]
             }
        else:
            # Unsupported protocol for V2Ray JSON (e.g. Hysteria might need specific support)
            return None

        outbound = {
            "tag": tag,
            "protocol": proxy.protocol,
            "settings": settings,
            "streamSettings": stream_settings,
            "mux": {
                "enabled": False,
                "concurrency": -1
            }
        }

        # Handle Chaining (Dialer Proxy)
        # If the proxy object has a 'dialer_proxy' field (custom extension) in details
        # This matches e2.json: "sockopt": { "dialerProxy": "chain-proxy1" }
        dialer_proxy = details.get("dialerProxy") or details.get("dialer_proxy")
        if dialer_proxy:
             if "sockopt" not in stream_settings:
                 stream_settings["sockopt"] = {}
             stream_settings["sockopt"]["dialerProxy"] = dialer_proxy

        return outbound

def generate_v2ray_config(
    proxies: List[Proxy],
    region: str = "all",
    extra_outbounds: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Wrapper for V2RayGenerator.
    """
    generator = V2RayGenerator()
    config_dict = generator.generate(proxies, region, extra_outbounds)
    return json.dumps(config_dict, indent=2, ensure_ascii=False)
