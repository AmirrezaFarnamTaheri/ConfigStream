import logging
import binascii
from typing import Optional
from urllib.parse import parse_qs, unquote
from ..models import Proxy
from .base import normalize_proxy_details, safe_b64_decode

logger = logging.getLogger(__name__)


def parse_ss(config: str) -> Optional[Proxy]:
    """Parse a Shadowsocks (ss://) URL."""
    try:
        if not config.startswith("ss://"):
            return None

        # Separate remark and query from the main part
        parts = config[5:].split("#", 1)
        main_part = parts[0]
        remark_part = parts[1] if len(parts) > 1 else ""
        remark_str, _, query_str = remark_part.partition("?")
        remark = unquote(remark_str)
        details = {k: v[0] for k, v in parse_qs(query_str).items()}

        # The part before the @ is either plain text or base64 encoded
        if "@" in main_part:
            user_info, host_info = main_part.split("@", 1)

            # Optimization: If it contains ':', it's definitely not standard Base64
            # (which uses +/ or -_). Treat as plain method:password to avoid log warning.
            if ":" not in user_info:
                try:
                    decoded_user_info = safe_b64_decode(user_info)
                    if decoded_user_info is not None and ":" in decoded_user_info:
                        user_info = decoded_user_info
                except (binascii.Error, ValueError):
                    pass  # Not base64, proceed
        else:
            # SIP002: ss://<base64-encoded-part>
            decoded_main = safe_b64_decode(main_part)
            if decoded_main is None or "@" not in decoded_main:
                return None
            user_info, host_info = decoded_main.split("@", 1)

        # Parse user_info
        if ":" not in user_info:
            return None
        method, password = user_info.split(":", 1)

        # Parse host_info
        if ":" not in host_info:
            return None
        host, port_str = host_info.rsplit(":", 1)

        try:
            port = int(port_str)
        except (ValueError, TypeError):
            logger.debug(f"Invalid port in shadowsocks config: {port_str}")
            return None
        if not (1 <= port <= 65535) or not host:
            return None

        # [FIX] Strict validation to reject garbage methods
        # Common valid ciphers (including 2022 and AEAD)
        # We don't want to maintain a perfect list, but we want to blacklist obvious garbage.
        invalid_methods = {
            "ss",
            "shadowsocks",
            "",
            "none",
            "null",
            "default",
            "cipher",
            "aes",
            "chacha20",  # incomplete names
        }
        if method.lower() in invalid_methods or len(method) < 3:
            # Most ciphers are > 3 chars (rc4-md5 is 7). 'aes' is ambiguous.
            logger.debug(
                f"Invalid Shadowsocks method detected: {method} in {config[:50]}..."
            )
            return None

        # [FIX] Enforce mandatory password
        if not password:
            return None

        # Fix plugin format: if plugin exists, ensure plugin_opts is extracted
        # Often format is: plugin=obfs-local;obfs=http;obfs-host=google.com
        if "plugin" in details:
            plugin_str = details["plugin"]
            # If plugin contains options separated by ;
            if ";" in plugin_str:
                plugin_parts = plugin_str.split(";")
                details["plugin"] = plugin_parts[0]
                if len(plugin_parts) > 1:
                    details["plugin_opts"] = ";".join(plugin_parts[1:])

        details.update({"method": method, "password": password})

        proxy = Proxy(
            config=config,
            protocol="shadowsocks",
            address=host.strip("[]"),  # Handle IPv6
            port=port,
            remarks=remark,
            details=details,
        )
        normalize_proxy_details(proxy)
        return proxy
    except (ValueError, IndexError, binascii.Error) as e:
        # [FIX] Downgrade to DEBUG to reduce log spam from mixed sources
        logger.debug(
            f"Failed to parse Shadowsocks config: {str(e)[:100]} | Context: {config[:50]}..."
        )
        return None


def parse_ss2022(config: str) -> Optional[Proxy]:
    """Parse a Shadowsocks 2022 (ss2022://) URL - uses same format as SS."""
    try:
        if not config.startswith("ss2022://"):
            return None

        # Convert ss2022:// to ss:// format for parsing
        ss_config = "ss://" + config[9:]
        proxy = parse_ss(ss_config)

        if proxy:
            # Update the original config and protocol
            proxy.config = config
            proxy.protocol = "ss2022"

        return proxy
    except Exception as e:
        logger.debug(f"Failed to parse Shadowsocks 2022: {e}")
        return None
