# SPDX-License-Identifier: AGPL-3.0-or-later
import html
import logging
import urllib.parse
from configstream.models import Proxy
from .base import normalize_proxy_details

logger = logging.getLogger(__name__)


def parse_vless(url: str) -> Proxy | None:
    url = html.unescape(url)
    """
    Parses a VLESS URL into a Proxy object.
    Format: vless://uuid@host:port?params#name
    """
    try:
        if not url.startswith("vless://"):
            return None

        # Remove "vless://"
        main_part = url[8:]

        # Split #name
        name = ""
        if "#" in main_part:
            main_part, name = main_part.split("#", 1)
            name = urllib.parse.unquote(name).strip()

        # Split ?params
        params_str = ""
        if "?" in main_part:
            main_part, params_str = main_part.split("?", 1)

        # Split uuid@host:port (rsplit handles @ in uuid edge case)
        if "@" not in main_part:
            return None
        uuid_val, host_port = main_part.rsplit("@", 1)

        # Handle host:port (IPv6 might have brackets)
        host = ""
        port = 0

        if host_port.startswith("["):
            # IPv6
            end_bracket = host_port.find("]")
            if end_bracket == -1:
                return None
            host = host_port[1:end_bracket]
            remaining = host_port[end_bracket + 1 :]
            if remaining.startswith(":"):
                try:
                    port = int(remaining[1:])
                except ValueError:
                    return None
            else:
                port = 443  # Default?
        else:
            if ":" in host_port:
                host, port_str = host_port.rsplit(":", 1)
                try:
                    port = int(port_str)
                except ValueError:
                    return None
            else:
                host = host_port
                port = 443

        # Parse Params
        params = {}
        if params_str:
            for pair in params_str.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    params[k] = urllib.parse.unquote(v)

        uuid_val = uuid_val.strip()
        if not uuid_val:
            for key in ("uuid", "id", "user", "userid", "uid"):
                val = params.get(key)
                if isinstance(val, str) and val.strip():
                    uuid_val = val.strip()
                    break

        # Validation (Relaxed)
        if not host or not port or not uuid_val:
            return None

        flow_value = params.get("flow", "")
        if flow_value.strip().lower() == "xtls-rprx-direct":
            # Removed in modern sing-box/xray cores; reject at parse stage.
            return None

        # Construct Proxy
        # Ensure Pydantic model "config" field is populated
        proxy = Proxy(
            config=url,  # Add config field
            protocol="vless",
            address=host,
            port=port,
            details={
                "uuid": uuid_val,
                "name": name,
                "type": params.get("type", "tcp"),
                "security": params.get("security", "none"),
                "encryption": params.get("encryption", "none"),
                "flow": flow_value,
            },
        )

        # Also set UUID on proxy object if model has it
        if hasattr(proxy, "uuid"):
            proxy.uuid = uuid_val
        if hasattr(proxy, "remarks"):
            proxy.remarks = name

        # Standard Transport Params
        if "sni" in params:
            proxy.details["sni"] = params["sni"]
        elif params.get("security") == "tls":
            proxy.details["sni"] = host  # Default SNI to host for TLS

        # Reality params (check common aliases)
        pbk = next(
            (
                params.get(k)
                for k in ("pbk", "publicKey", "public-key")
                if params.get(k)
            ),
            None,
        )
        if pbk:
            proxy.details["pbk"] = pbk

        sid = next(
            (params.get(k) for k in ("sid", "shortId", "short-id") if params.get(k)),
            None,
        )
        if sid:
            proxy.details["sid"] = sid

        if "fp" in params:
            # Store as "fp" directly so converters find it for all TLS modes
            proxy.details["fp"] = params["fp"]
        if "alpn" in params:
            proxy.details["alpn"] = params["alpn"]

        # Transport params
        transport = params.get("type")
        if transport in ("ws", "http", "h2", "httpupgrade"):
            proxy.details["path"] = params.get("path", "/")
            if "host" in params:
                proxy.details["host"] = params["host"]
        elif transport == "grpc":
            proxy.details["serviceName"] = params.get("serviceName", "")

        normalize_proxy_details(proxy)
        return proxy

    except Exception:
        return None
