from typing import Dict, Any, Optional
import logging

from ..models import Proxy

logger = logging.getLogger(__name__)


def to_clash_proxy(proxy: Proxy) -> Optional[Dict[str, Any]]:
    """
    Converts a Proxy object into a Clash proxy dictionary.
    Returns None if the protocol is not supported or conversion fails.
    """
    if not proxy.is_working:
        return None

    try:
        common = {
            "name": f"{proxy.country_code}-{proxy.protocol}-{proxy.id[:6]}",
            "server": proxy.address,
            "port": proxy.port,
            "type": proxy.protocol,
        }

        if proxy.protocol == "ss" or proxy.protocol == "shadowsocks":
            common["type"] = "ss"
            common["cipher"] = (
                proxy.details.get("method")
                or proxy.details.get("cipher")
                or "chacha20-ietf-poly1305"
            )
            common["password"] = proxy.details.get("password") or proxy.uuid
            # Add plugin support if needed
            if proxy.details.get("plugin"):
                common["plugin"] = proxy.details["plugin"]
                common["plugin-opts"] = proxy.details.get("plugin_opts", {})
            return common

        elif proxy.protocol == "vmess":
            common["uuid"] = proxy.uuid
            common["alterId"] = proxy.details.get("alterId", 0)
            common["cipher"] = (
                proxy.details.get("scy") or proxy.details.get("cipher") or "auto"
            )

            # Transport
            net = proxy.details.get("network", "tcp")
            common["network"] = net
            if net == "ws":
                common["ws-opts"] = {
                    "path": proxy.details.get("path", "/"),
                    "headers": {"Host": proxy.details.get("host", "")},
                }
            elif net == "grpc":
                common["grpc-opts"] = {
                    "grpc-service-name": proxy.details.get("serviceName", "")
                }

            # TLS
            if proxy.details.get("security") == "tls":
                common["tls"] = True
                if proxy.details.get("sni"):
                    common["servername"] = proxy.details["sni"]
                if proxy.details.get("fp"):
                    common["client-fingerprint"] = proxy.details["fp"]

            return common

        elif proxy.protocol == "trojan":
            common["password"] = proxy.uuid
            if proxy.details.get("sni"):
                common["sni"] = proxy.details["sni"]
            if proxy.details.get("security") == "tls":
                common["udp"] = True
            return common

        # Basic VLESS support (Clash Meta/Premium only usually, but often mapped)
        elif proxy.protocol == "vless":
            common["uuid"] = proxy.uuid
            common["flow"] = proxy.details.get("flow", "")

            # Transport & TLS similar to VMess
            net = proxy.details.get("network", "tcp")
            common["network"] = net
            if net == "ws":
                common["ws-opts"] = {
                    "path": proxy.details.get("path", "/"),
                    "headers": {"Host": proxy.details.get("host", "")},
                }
            if proxy.details.get("security") == "tls":
                common["tls"] = True
                if proxy.details.get("sni"):
                    common["servername"] = proxy.details["sni"]
                if proxy.details.get("fp"):
                    common["client-fingerprint"] = proxy.details["fp"]
            elif proxy.details.get("security") == "reality":
                # Clash Meta specific Reality fields
                common["tls"] = True
                common["servername"] = proxy.details.get("sni", "")
                common["reality-opts"] = {
                    "public-key": proxy.details.get("pbk", ""),
                    "short-id": proxy.details.get("sid", ""),
                }
                if proxy.details.get("fp"):
                    common["client-fingerprint"] = proxy.details["fp"]

            return common

        # Fallback or unknown
        return None

    except Exception as e:
        logger.debug(f"Failed to convert proxy {proxy.id} to Clash: {e}")
        return None
