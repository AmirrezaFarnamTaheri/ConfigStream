# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import binascii
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, unquote
from ..models import Proxy
from .base import normalize_proxy_details, safe_b64_decode
from ..constants import MAX_CONFIG_LINE_LENGTH
from ..security_validator import SecurityValidator

logger = logging.getLogger(__name__)


def _safe_log_text(value: object) -> str:
    return SecurityValidator.sanitize_log_message(str(value))


def parse_ss(config: str) -> Optional[Proxy]:
    """Parse a Shadowsocks (ss://) URL."""
    try:
        config = config.strip()
        if MAX_CONFIG_LINE_LENGTH > 0 and len(config) > MAX_CONFIG_LINE_LENGTH:
            return None

        if not config.startswith("ss://"):
            return None

        # Separate remark and query from the main part
        # Logic: query starts with '?' if present.
        # But '?' can be part of remark too? Usually URI standard: #fragment? No, ?query#fragment.
        # But SS links are weird.
        # Often: ss://BASE64#remark

        # Handle '#' for remark (some providers append query params after fragment)
        parts = config[5:].split("#", 1)
        main_part = parts[0]

        details: Dict[str, Any] = {}
        remark = ""
        if len(parts) > 1:
            frag = parts[1]
            remark_str, sep, frag_query = frag.partition("?")
            remark = unquote(remark_str)
            if sep and frag_query:
                q_params = parse_qs(frag_query)
                details.update({k: v[0] for k, v in q_params.items() if v})

        # Check for query parameters inside main_part (not standard but possible) or after?
        # Standard SIP002 doesn't use query params heavily except for plugins maybe?
        # Usually plugin params are in the user_info part or decoded part.

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
            # Decode the whole thing
            decoded_main = safe_b64_decode(main_part)
            if decoded_main is None:
                # Fallback: maybe it's classic format without @?
                return None

            if "@" in decoded_main:
                user_info, host_info = decoded_main.split("@", 1)
            else:
                # Classic format: method:password:ip:port
                parts_classic = decoded_main.split(":")
                if len(parts_classic) >= 4:
                    port_str = parts_classic[-1]
                    host = parts_classic[-2]
                    password = parts_classic[-3]
                    method = ":".join(parts_classic[:-3])
                    user_info = f"{method}:{password}"
                    host_info = f"{host}:{port_str}"
                else:
                    return None

        # Parse user_info
        if ":" not in user_info:
            return None
        method, password = user_info.split(":", 1)
        if not password:
            for key in ("password", "psk", "pass", "pwd"):
                val = details.get(key, "")
                if isinstance(val, str) and val.strip():
                    password = val.strip()
                    break
            # Drop proxy if password still missing after all fallback attempts
            if not password:
                logger.debug(
                    "Shadowsocks proxy dropped: no password after fallback check"
                )
                return None

        # Parse host_info
        # Check for plugin params (SIP003 simple-obfs etc often appended as /?plugin=...)
        # But usually in SS links, plugins are encoded.

        # Strip query params from host_info (SIP003 plugin params)
        for sep in ("/?", "?"):
            if sep in host_info:
                host_info, query = host_info.split(sep, 1)
                details.update({k: v[0] for k, v in parse_qs(query).items() if v})
                break

        if ":" not in host_info:
            return None
        host, port_str = host_info.rsplit(":", 1)

        try:
            port = int(port_str)
        except (ValueError, TypeError):
            logger.debug(
                "Invalid port in shadowsocks config: %s",
                _safe_log_text(port_str),
            )
            return None
        if not (1 <= port <= 65535) or not host:
            return None

        # Strict validation to reject garbage methods
        invalid_methods = {
            "ss",
            "shadowsocks",
            "",
            "null",
            "default",
            "cipher",
            "aes",
            "chacha20",  # incomplete names
        }
        # Relaxed length check to allow older short methods (e.g. rc4)
        if method.lower() in invalid_methods or len(method) < 2:
            logger.debug(
                "Invalid Shadowsocks method detected: %s",
                _safe_log_text(method),
            )
            return None

        if not password:
            return None

        # Fix plugin format: if plugin exists, ensure plugin_opts is extracted
        # Often format is: plugin=obfs-local;obfs=http;obfs-host=google.com
        if "plugin" in details:
            plugin_str = details["plugin"]
            # If plugin contains options separated by ;
            if ";" in plugin_str:
                plugin_parts = plugin_str.split(";")
                details["plugin"] = plugin_parts[
                    0
                ]  # The actual plugin name (e.g. obfs-local)
                if len(plugin_parts) > 1:
                    # The rest are options
                    details["plugin_opts"] = ";".join(plugin_parts[1:])

        server = host.strip("[]")
        details.update(
            {
                "method": method,
                "password": password,
                "server": server,
                "port": port,
            }
        )

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
        logger.debug(
            "Failed to parse Shadowsocks config: %s",
            _safe_log_text(str(e)[:100]),
        )
        return None


def parse_ss2022(config: str) -> Optional[Proxy]:
    """Parse a Shadowsocks 2022 (ss2022://) URL - uses same format as SS."""
    try:
        config = config.strip()
        if MAX_CONFIG_LINE_LENGTH > 0 and len(config) > MAX_CONFIG_LINE_LENGTH:
            return None

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
        logger.debug("Failed to parse Shadowsocks 2022: %s", _safe_log_text(e))
        return None
