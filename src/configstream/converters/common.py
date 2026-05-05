# SPDX-License-Identifier: AGPL-3.0-or-later
import base64
import logging
from typing import Any, Optional
import urllib.parse
from ..models import Proxy
from ..security_validator import SecurityValidator
from ..tagging import get_flag_emoji

logger = logging.getLogger(__name__)


def safe_int_conversion(value: Any, default: int = 0) -> int:
    """
    Safely convert a value to int, handling bytes and other types.
    """
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, bytes):
        try:
            return int(value.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            try:
                return int.from_bytes(value, byteorder="big", signed=False)
            except (ValueError, OverflowError):
                return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def to_uri(proxy: Proxy) -> Optional[str]:
    """
    Reconstructs a URI from a Proxy object.
    Supports basic protocols: vmess, vless, trojan, ss.
    """
    if not proxy.is_working:
        return None

    # Revived/chain proxies are multi-hop configs that cannot be expressed
    # as a single URI.  Return None so they are excluded from URI subscriptions.
    # (The plaintext generator has its own _extract_uri that handles these.)
    if proxy.protocol == "revived" or (proxy.config or "").startswith("revived://"):
        return None

    # Attempt to use the original config if it looks like a URI
    if proxy.config and "://" in proxy.config:
        # Just return it, maybe append name
        return proxy.config

    # Otherwise, try to reconstruct based on parsed details
    # This is a simplified reconstruction for export purposes
    try:
        if proxy.protocol == "shadowsocks":
            # ss://user:pass@host:port#name
            # user info usually base64 encoded
            cipher = (
                proxy.details.get("method")
                or proxy.details.get("cipher")
                or "chacha20-ietf-poly1305"
            )
            password = proxy.details.get("password") or ""
            userinfo = f"{cipher}:{password}"
            b64_userinfo = (
                base64.urlsafe_b64encode(userinfo.encode()).decode().rstrip("=")
            )
            name = (
                proxy.remarks
                or get_flag_emoji(proxy.country_code)
                or proxy.country_code
            )
            return f"ss://{b64_userinfo}@{proxy.address}:{proxy.port}#{urllib.parse.quote(name)}"

        elif proxy.protocol == "trojan":
            # trojan://password@host:port?params#name
            password = proxy.uuid
            name = (
                proxy.remarks
                or get_flag_emoji(proxy.country_code)
                or proxy.country_code
            )
            # Include transport and TLS query params so clients can connect
            # when proxy uses ws/grpc/h2 transport (standard Trojan share link format)
            params: dict[str, str] = {}
            details = proxy.details or {}
            net = details.get("net") or details.get("network") or details.get("type")
            if net and net != "tcp":
                params["type"] = net
                if details.get("path"):
                    params["path"] = str(details["path"])
                if details.get("host"):
                    params["host"] = str(details["host"])
                if details.get("serviceName"):
                    params["serviceName"] = str(details["serviceName"])
            security = details.get("security") or ""
            if details.get("sni"):
                params["sni"] = str(details["sni"])
            if security == "reality":
                params["security"] = "reality"
                if details.get("pbk"):
                    params["pbk"] = str(details["pbk"])
                if details.get("sid"):
                    params["sid"] = str(details["sid"])
                if details.get("fp"):
                    params["fp"] = str(details["fp"])
            elif details.get("tls") or security == "tls":
                params["security"] = "tls"
            if details.get("fp") and "fp" not in params:
                params["fp"] = str(details["fp"])
            query = urllib.parse.urlencode(params) if params else ""
            uri = f"trojan://{password}@{proxy.address}:{proxy.port}"
            if query:
                uri += f"?{query}"
            uri += f"#{urllib.parse.quote(name)}"
            return uri

        elif proxy.protocol in ["vmess", "vless"]:
            # These are complex JSONs usually, or complex URIs
            # For now, if we don't have the original URI, we skip reconstruction to avoid bad configs
            return None

    except (UnicodeDecodeError, ValueError, AttributeError, KeyError) as e:
        # Expected errors from malformed proxy details
        safe_proxy = SecurityValidator.sanitize_log_message(str(proxy.address))
        safe_error = SecurityValidator.sanitize_log_message(str(e))
        logger.debug("URI reconstruction failed for %s: %s", safe_proxy, safe_error)
    except Exception as e:
        # Unexpected errors - log as warning for debugging
        safe_proxy = SecurityValidator.sanitize_log_message(str(proxy.address))
        safe_error = SecurityValidator.sanitize_log_message(str(e))
        logger.warning(
            "Unexpected error in URI reconstruction for %s: %s",
            safe_proxy,
            safe_error,
        )

    return None
