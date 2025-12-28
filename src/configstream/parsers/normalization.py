import logging

from ..models import Proxy

logger = logging.getLogger(__name__)


def normalize_proxy_details(proxy: Proxy) -> None:
    """
    Standardizes common proxy attributes (sni, path, etc.) from the
    protocol-specific `details` dictionary into top-level keys for easier access
    and deduplication. This mutates the proxy object.
    """
    if not proxy.details:
        return

    # 1. Standardize SNI (Server Name Indication) / Host
    # Order of precedence: 'sni' > 'peer' > 'host' (from details)
    sni = (
        proxy.details.get("sni")
        or proxy.details.get("peer")
        or proxy.details.get("host")
    )
    if sni:
        proxy.details["sni"] = str(sni)

    # For VMess, SNI takes precedence from the 'Host' header if present.
    if proxy.protocol == "vmess":
        headers = proxy.details.get("headers")
        if isinstance(headers, dict) and "Host" in headers:
            proxy.details["sni"] = headers["Host"]

    # For Shadowsocks, SNI can be in plugin opts
    if proxy.protocol == "shadowsocks" and "plugin" in proxy.details:
        plugin_str = proxy.details.get("plugin", "")
        if isinstance(plugin_str, str):
            plugin_opts = dict(
                item.split("=") for item in plugin_str.split(";") if "=" in item
            )
            if "obfs-host" in plugin_opts:
                proxy.details.setdefault("sni", plugin_opts["obfs-host"])
            if "obfs-uri" in plugin_opts:
                proxy.details.setdefault("path", plugin_opts["obfs-uri"])

    # 2. Standardize Path
    # Order of precedence: 'path' > 'serviceName'
    path = proxy.details.get("path") or proxy.details.get("serviceName")
    if path:
        proxy.details["path"] = str(path)

    # 3. Standardize ALPN (Application-Layer Protocol Negotiation)
    alpn = proxy.details.get("alpn")
    if alpn:
        if isinstance(alpn, str):
            # Can be comma-separated
            alpn_list = [s.strip() for s in alpn.split(",")]
            proxy.details["alpn"] = alpn_list
            logger.debug(f"Normalized ALPN for {proxy.id[:8]}: {alpn_list}")
        elif isinstance(alpn, (list, tuple)):
            proxy.details["alpn"] = [str(item) for item in alpn]
