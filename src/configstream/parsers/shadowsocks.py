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
                    if ":" in decoded_user_info:
                        user_info = decoded_user_info
                except (binascii.Error, ValueError):
                    pass  # Not base64, proceed
        else:
            # SIP002: ss://<base64-encoded-part>
            decoded_main = safe_b64_decode(main_part)
            if "@" not in decoded_main:
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
            logger.debug("Invalid port in shadowsocks config: %s", port_str)
            return None
        if not (1 <= port <= 65535) or not host:
            return None

        # [FIX] Basic validation to reject garbage methods like "ss"
        if method.lower() in ["ss", "shadowsocks", ""]:
            logger.debug(
                f"Invalid Shadowsocks method detected: {method} in {config[:50]}..."
            )
            return None

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
        # [FIX] Elevated to WARNING for visibility on bad sources
        logger.warning(
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
        logger.debug("Failed to parse Shadowsocks 2022: %s", e)
        return None
