from typing import Any, Optional
import urllib.parse
from ..models import Proxy


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
            import base64

            cipher = proxy.details.get("method") or proxy.details.get("cipher") or "chacha20-ietf-poly1305"
            password = proxy.details.get("password") or ""
            userinfo = f"{cipher}:{password}"
            b64_userinfo = (
                base64.urlsafe_b64encode(userinfo.encode()).decode().rstrip("=")
            )
            return f"ss://{b64_userinfo}@{proxy.address}:{proxy.port}#{urllib.parse.quote(proxy.country_code)}"

        elif proxy.protocol == "trojan":
            # trojan://password@host:port#name
            password = proxy.uuid
            return f"trojan://{password}@{proxy.address}:{proxy.port}#{urllib.parse.quote(proxy.country_code)}"

        elif proxy.protocol in ["vmess", "vless"]:
            # These are complex JSONs usually, or complex URIs
            # For now, if we don't have the original URI, we skip reconstruction to avoid bad configs
            return None

    except Exception:
        pass

    return None
