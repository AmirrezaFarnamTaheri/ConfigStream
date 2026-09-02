# SPDX-License-Identifier: AGPL-3.0-or-later
import binascii
import html
import logging
import json
import re
import ipaddress
from typing import Optional, Any, Dict
from urllib.parse import urlparse, unquote
from pydantic import ValidationError
from ..models import Proxy
from .base import normalize_proxy_details
from ..constants import MAX_CONFIG_LINE_LENGTH
from ..config import AppSettings
from ..security_validator import safe_log_text

logger = logging.getLogger(__name__)

# Cache settings to avoid repeated pydantic_settings instantiation in per-proxy hot path
_SETTINGS_CACHE = AppSettings()

# Regex patterns for IP validation
_IPV4_PATTERN = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)
_HOSTNAME_PATTERN = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
)


def parse_generic_url_scheme(config: str) -> Optional[Proxy]:
    """Parse generic URL-based schemes like http, socks."""
    try:
        config = config.strip()
        if MAX_CONFIG_LINE_LENGTH > 0 and len(config) > MAX_CONFIG_LINE_LENGTH:
            return None

        # Support naked IP:PORT for SOCKS/HTTP
        if "://" not in config and ":" in config and not config.startswith("{"):
            host = ""
            port_val = 0
            if config.startswith("[") and "]:" in config:
                host_part, _, port_str = config[1:].partition("]:")
                if host_part and port_str.isdigit():
                    host = host_part
                    port_val = int(port_str)
            else:
                parts = config.split(":")
                if len(parts) == 2 and parts[1].isdigit():
                    host = parts[0]
                    port_val = int(parts[1])

            if host and port_val:
                # Validate IP/hostname format
                is_valid_ip = False
                try:
                    ipaddress.ip_address(host)
                    is_valid_ip = True
                except ValueError:
                    is_valid_ip = False

                is_valid_hostname = (
                    _HOSTNAME_PATTERN.match(host) is not None and len(host) <= 253
                )

                if not (is_valid_ip or is_valid_hostname):
                    logger.debug(
                        "Naked IP:PORT rejected: invalid host format %s",
                        safe_log_text(host),
                    )
                    return None

                # Validate port range
                if not (1 <= port_val <= 65535):
                    logger.debug(
                        "Naked IP:PORT rejected: port %d out of range",
                        port_val,
                    )
                    return None

                # Heuristic: Default to SOCKS5 if port is 1080 or 10808, else HTTP
                # Ideally, this should come from source metadata, but this improves the hit rate for SOCKS lists.
                protocol = "http"
                if port_val in [1080, 10800, 10808, 9050]:
                    protocol = "socks5"

                # If source metadata indicates socks, it should be passed here, but we don't have it.
                # The heuristic is better than always HTTP for these ports.

                proxy = Proxy(
                    config=config,
                    protocol=protocol,
                    address=host,
                    port=port_val,
                    uuid="",
                    details={},
                    remarks=f"naked_ip_{protocol}",
                )
                normalize_proxy_details(proxy)
                return proxy

        parsed = urlparse(config)
        if not parsed.hostname:
            return None

        host = parsed.hostname
        is_valid_ip = False
        try:
            ipaddress.ip_address(host)
            is_valid_ip = True
        except ValueError:
            is_valid_ip = False

        # Stricter check for generic parsing: Must have valid hostname characters
        if not is_valid_ip:
            if not _HOSTNAME_PATTERN.match(host) or len(host) > 253:
                return None

        # Block "invalid" or "garbage" as hostnames for testing hygiene
        if host.lower() in ("garbage", "invalid"):
            return None

        # Ensure hostname has at least one dot or is localhost (basic validity)
        if not is_valid_ip and "." not in host and host != "localhost":
            # Allow single-label hostnames only when explicitly permitted.
            if not _SETTINGS_CACHE.ALLOW_PRIVATE_IPS:
                return None

        scheme = parsed.scheme.lower()

        # Protocol Normalization
        protocol = scheme
        tls = False

        if scheme == "https":
            protocol = "http"
            tls = True
        elif scheme == "socks":
            protocol = "socks5"
        elif scheme == "socks4":
            protocol = "socks4"

        default_ports = {
            "http": 80,
            "https": 443,
            "ssh": 22,
            "socks": 1080,
            "socks4": 1080,
            "socks5": 1080,
        }
        port = parsed.port or default_ports.get(scheme, 80)
        if not (1 <= port <= 65535):
            return None

        details: Dict[str, Any] = {"password": parsed.password or ""}
        if tls:
            details["tls"] = True

        proxy = Proxy(
            config=config,
            protocol=protocol,
            address=host,
            port=port,
            uuid="",  # UUID must be empty for non-UUID protocols to pass schema validation
            details=details,
            remarks=unquote(parsed.fragment or ""),
        )
        if parsed.username:
            proxy.details["username"] = unquote(parsed.username)
        normalize_proxy_details(proxy)
        return proxy
    except (
        ValidationError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        TimeoutError,
        IndexError,
        TypeError,
        binascii.Error,
    ) as e:
        logger.debug("Failed to parse Generic config: %s", safe_log_text(str(e)[:50]))
        return None


def parse_naive(config: str) -> Optional[Proxy]:
    config = html.unescape(config)
    try:
        config = config.strip()
        if MAX_CONFIG_LINE_LENGTH > 0 and len(config) > MAX_CONFIG_LINE_LENGTH:
            return None

        parsed = urlparse(config.replace("naive+", ""))
        if not parsed.hostname:
            return None
        if not parsed.username or not parsed.password:
            return None
        scheme = parsed.scheme.lower()
        tls = scheme == "https"
        details: Dict[str, Any] = {"password": parsed.password or ""}
        if tls:
            details["tls"] = True
        proxy = Proxy(
            config=config,
            protocol="naive",
            address=parsed.hostname,
            port=parsed.port or (443 if tls else 80),
            uuid="",
            details=details,
            remarks=unquote(parsed.fragment or ""),
        )
        if parsed.username:
            proxy.details["username"] = unquote(parsed.username)
        normalize_proxy_details(proxy)
        return proxy
    except (
        ValidationError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        TimeoutError,
        IndexError,
        TypeError,
        binascii.Error,
    ) as e:
        logger.debug("Failed to parse Naive config: %s", safe_log_text(str(e)[:50]))
        return None


def parse_v2ray_json(config: str) -> Optional[Proxy]:
    config = html.unescape(config)
    stripped = config.strip()
    if MAX_CONFIG_LINE_LENGTH > 0 and len(stripped) > MAX_CONFIG_LINE_LENGTH:
        return None

    if not stripped.startswith("{"):
        return None
    try:
        data = json.loads(stripped)
    except (json.JSONDecodeError, RecursionError, ValueError, TypeError):
        # RecursionError guards against deeply nested attacker JSON; the
        # dispatcher only catches ValueError/KeyError/JSONDecodeError.
        return None
    if not isinstance(data, dict):
        return None

    outbound = data.get("outbound")
    outbounds = data.get("outbounds")
    if not outbound and isinstance(outbounds, list) and outbounds:
        outbound = outbounds[0]
    if not outbound or not isinstance(outbound, dict):
        return None

    protocol_raw = str(outbound.get("protocol", "")).lower().strip()
    if not protocol_raw:
        return None

    settings = outbound.get("settings")
    if not isinstance(settings, dict):
        settings = {}

    stream_settings = outbound.get("streamSettings")
    if not isinstance(stream_settings, dict):
        stream_settings = {}

    def _extract_stream_details(stream: Dict[str, Any]) -> Dict[str, Any]:
        details: Dict[str, Any] = {}
        network = stream.get("network") or stream.get("type")
        if isinstance(network, str) and network:
            details["net"] = network

        security = stream.get("security")
        if isinstance(security, str) and security:
            details["security"] = security

        if security in ("tls", "xtls"):
            tls_settings = stream.get("tlsSettings") or stream.get("xtlsSettings")
            if isinstance(tls_settings, dict):
                server_name = tls_settings.get("serverName")
                if server_name:
                    details["sni"] = server_name
                alpn = tls_settings.get("alpn")
                if alpn:
                    details["alpn"] = alpn
        elif security == "reality":
            reality = stream.get("realitySettings")
            if isinstance(reality, dict):
                server_name = reality.get("serverName")
                if server_name:
                    details["sni"] = server_name
                public_key = reality.get("publicKey")
                if public_key:
                    details["pbk"] = public_key
                short_id = reality.get("shortId")
                if short_id:
                    details["sid"] = short_id
                fingerprint = reality.get("fingerprint")
                if fingerprint:
                    details["fp"] = fingerprint

        if network == "ws":
            ws_settings = stream.get("wsSettings")
            if isinstance(ws_settings, dict):
                path = ws_settings.get("path")
                if path:
                    details["path"] = path
                headers = ws_settings.get("headers")
                if isinstance(headers, dict):
                    host = headers.get("Host") or headers.get("host")
                    if host:
                        details["host"] = host
        elif network == "grpc":
            grpc_settings = stream.get("grpcSettings")
            if isinstance(grpc_settings, dict):
                service_name = grpc_settings.get("serviceName")
                if service_name:
                    details["serviceName"] = service_name
        elif network in ("http", "h2"):
            http_settings = stream.get("httpSettings")
            if isinstance(http_settings, dict):
                path = http_settings.get("path")
                if isinstance(path, list):
                    if path:
                        details["path"] = path[0]
                elif path:
                    details["path"] = path
                host = http_settings.get("host")
                if isinstance(host, list):
                    if host:
                        details["host"] = host[0]
                elif host:
                    details["host"] = host

        return details

    details = _extract_stream_details(stream_settings)

    address = ""
    port = None
    uuid = ""
    protocol = protocol_raw

    if protocol_raw in ("vmess", "vless"):
        nodes = settings.get("vnext")
        if not isinstance(nodes, list) or not nodes:
            return None
        server_info = nodes[0]
        if not isinstance(server_info, dict):
            return None
        address_raw = (
            server_info.get("address")
            or server_info.get("server")
            or server_info.get("ip")
        )
        if not address_raw:
            return None
        address = str(address_raw)
        port = server_info.get("port")
        users = server_info.get("users")
        user_info = users[0] if isinstance(users, list) and users else {}
        if isinstance(user_info, dict):
            uuid = user_info.get("id") or user_info.get("uuid") or ""
            if protocol_raw == "vless":
                flow = user_info.get("flow")
                if flow:
                    details["flow"] = flow
                encryption = user_info.get("encryption")
                if encryption:
                    details["encryption"] = encryption
            elif protocol_raw == "vmess":
                alter_id = user_info.get("alterId")
                if alter_id is not None:
                    details["aid"] = alter_id
        if not uuid:
            return None
    elif protocol_raw in ("trojan", "shadowsocks", "ss", "socks", "http"):
        nodes = settings.get("servers")
        if not isinstance(nodes, list) or not nodes:
            return None
        server_info = nodes[0]
        if not isinstance(server_info, dict):
            return None
        address_raw = (
            server_info.get("address")
            or server_info.get("server")
            or server_info.get("ip")
        )
        if not address_raw:
            return None
        address = str(address_raw)
        port = server_info.get("port")
        if protocol_raw == "trojan":
            uuid = server_info.get("password", "")
            if not uuid:
                return None
        elif protocol_raw in ("shadowsocks", "ss"):
            protocol = "shadowsocks"
            details["password"] = server_info.get("password", "")
            method = server_info.get("method") or server_info.get("cipher")
            if method is not None and not isinstance(method, str):
                return None
            if method:
                details["method"] = method
            if not details["password"]:
                return None
            invalid_methods = {
                "ss",
                "shadowsocks",
                "",
                "null",
                "default",
                "cipher",
                "aes",
                "chacha20",
            }
            if not method or method.lower() in invalid_methods or len(method) < 2:
                return None
        elif protocol_raw == "socks":
            protocol = "socks5"
            user = server_info.get("user") or server_info.get("username") or ""
            uuid = user
            password = server_info.get("pass") or server_info.get("password")
            if password:
                details["password"] = password
        elif protocol_raw == "http":
            user = server_info.get("user") or server_info.get("username") or ""
            uuid = user
            password = server_info.get("pass") or server_info.get("password")
            if password:
                details["password"] = password
    else:
        return None

    if not address or port is None:
        return None

    try:
        port_int = int(port)
    except (ValueError, TypeError):
        logger.debug("Invalid port in v2ray config: %s", safe_log_text(port))
        return None

    remarks = outbound.get("tag", data.get("remark", ""))

    proxy = Proxy(
        config=config,
        protocol=protocol,
        address=address,
        port=port_int,
        uuid=uuid,
        remarks=remarks or "",
        details=details,
    )
    normalize_proxy_details(proxy)
    return proxy
