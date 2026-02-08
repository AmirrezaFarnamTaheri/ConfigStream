# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import urllib.parse
from configstream.models import Proxy
from .base import normalize_proxy_details

logger = logging.getLogger(__name__)


def parse_vless(url: str) -> Proxy | None:
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

        # Split uuid@host:port
        # Handle '@' in uuid or params incorrectly handled?
        # Standard VLESS format: uuid@host:port
        # Some encoded UUIDs might contain stuff? Unlikely.
        if "@" not in main_part:
            return None

        # Split from right to handle weird UUIDs? No, host:port is at end.
        # But if uuid contains '@', we should split on LAST @?
        # Standard is last @ before host.
        # Let's split on the LAST @
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
                "flow": params.get("flow", ""),
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

        # Handle aliases for Reality Public Key
        pbk = params.get("pbk")
        if not pbk:
            pbk = params.get("publicKey")
        if not pbk:
            pbk = params.get("public-key")

        if pbk:
            # Check if it's a list (unlikely from simple loop, but defensive)
            proxy.details["pbk"] = pbk

        # Handle aliases for Short ID
        sid = params.get("sid")
        if not sid:
            sid = params.get("shortId")
        if not sid:
            sid = params.get("short-id")

        if sid:
            proxy.details["sid"] = sid

        if "fp" in params:
            # [FIX] Store as "fp" directly so converters find it for all TLS modes
            proxy.details["fp"] = params["fp"]
        if "alpn" in params:
            proxy.details["alpn"] = params["alpn"]

        # WS / GRPC / HTTP transport params
        # [FIX] Store under standard keys that converters expect (path, host, serviceName)
        if params.get("type") == "ws":
            proxy.details["path"] = params.get("path", "/")
            if "host" in params:
                proxy.details["host"] = params["host"]

        elif params.get("type") == "grpc":
            proxy.details["serviceName"] = params.get("serviceName", "")

        elif params.get("type") in ["http", "h2"]:
            proxy.details["path"] = params.get("path", "/")
            if "host" in params:
                proxy.details["host"] = params["host"]

        normalize_proxy_details(proxy)
        return proxy

    except Exception:
        # logger.debug(f"Failed to parse VLESS: {e}")
        return None
