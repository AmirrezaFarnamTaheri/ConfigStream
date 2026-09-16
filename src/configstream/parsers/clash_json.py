# SPDX-License-Identifier: AGPL-3.0-or-later
import binascii
import json
import logging
from typing import Optional
from pydantic import ValidationError
from ..models import Proxy
from ..constants import MAX_CONFIG_LINE_LENGTH
from ..security_validator import SecurityValidator
from .base import normalize_proxy_details

logger = logging.getLogger(__name__)


def _string(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _plugin_opts(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return ";".join(f"{key}={value[key]}" for key in sorted(value))
    return ""


def _transport_details(data: dict) -> dict:
    """Map Clash transport/TLS fields into the closed public details schema."""

    details: dict = {}
    network = _string(data.get("network") or data.get("net"))
    if network:
        details["net"] = network
        details["type"] = network

    for key in (
        "path",
        "host",
        "serviceName",
        "grpc_service_name",
        "http_host",
        "ws_host",
        "http_path",
        "ws_path",
        "server_name",
        "detour",
        "tag",
    ):
        value = data.get(key)
        if value not in (None, ""):
            details[key] = value

    sni = data.get("sni") or data.get("servername") or data.get("server-name")
    if sni:
        details["sni"] = _string(sni)
    if "tls" in data:
        tls = data["tls"]
        details["tls"] = tls if isinstance(tls, dict) else _bool(tls)
    if "skip_cert_verify" in data:
        details["skip_cert_verify"] = _bool(data["skip_cert_verify"])
    elif "skip-cert-verify" in data:
        details["skip_cert_verify"] = _bool(data["skip-cert-verify"])
    if "allowInsecure" in data:
        details["allowInsecure"] = _bool(data["allowInsecure"])
    if "alpn" in data:
        details["alpn"] = data["alpn"]
    fingerprint = (
        data.get("fp") or data.get("client-fingerprint") or data.get("fingerprint")
    )
    if fingerprint:
        details["fp"] = _string(fingerprint)

    for key in ("has_utls", "has_alpn_rotation", "has_multiplexing"):
        if key in data:
            details[key] = _bool(data[key])

    ws_opts = data.get("ws-opts")
    if isinstance(ws_opts, dict):
        path = ws_opts.get("path")
        if path:
            details["path"] = _string(path)
        headers = ws_opts.get("headers")
        if isinstance(headers, dict):
            host = headers.get("Host") or headers.get("host")
            if host:
                details["host"] = _string(host)

    grpc_opts = data.get("grpc-opts")
    if isinstance(grpc_opts, dict):
        service = grpc_opts.get("grpc-service-name") or grpc_opts.get("service-name")
        if service:
            details["serviceName"] = _string(service)

    reality_opts = data.get("reality-opts")
    if isinstance(reality_opts, dict):
        public_key = reality_opts.get("public-key") or reality_opts.get("publicKey")
        short_id = reality_opts.get("short-id") or reality_opts.get("shortId")
        if public_key:
            details["pbk"] = _string(public_key)
        if short_id:
            details["sid"] = _string(short_id)
    return details


def _canonical_details(data: dict, protocol: str) -> dict:
    """Return protocol details without leaking raw Clash-only/vendor keys."""

    if protocol == "shadowsocks":
        details = {
            "method": _string(data.get("method") or data.get("cipher")),
            "password": _string(data.get("password")),
            "server": _string(data.get("server")),
            "port": int(data.get("port", 0)),
        }
        plugin = data.get("plugin")
        if isinstance(plugin, str) and plugin:
            details["plugin"] = plugin
        plugin_opts = _plugin_opts(data.get("plugin-opts"))
        if plugin_opts:
            details["plugin_opts"] = plugin_opts
        return details

    if protocol == "wireguard":
        details = {}
        aliases = {
            "private_key": ("private_key", "private-key", "privateKey"),
            "peer_public_key": ("peer_public_key", "public-key", "publicKey"),
            "pre_shared_key": ("pre_shared_key", "pre-shared-key", "preshared-key"),
            "reserved": ("reserved",),
            "mtu": ("mtu",),
            "local_address": ("local_address", "ip"),
        }
        for target, candidates in aliases.items():
            for candidate in candidates:
                if candidate in data and data[candidate] not in (None, ""):
                    details[target] = data[candidate]
                    break
        details["server"] = _string(data.get("server"))
        details["server_port"] = int(data.get("port", 0))
        return details

    details = _transport_details(data)
    if protocol == "vmess":
        details["uuid"] = _string(data.get("uuid"))
        alter_id = data.get("alterId", data.get("aid", 0))
        try:
            details["alterId"] = max(0, int(alter_id))
        except (TypeError, ValueError):
            details["alterId"] = 0
        security = data.get("security") or data.get("cipher")
        if security:
            details["security"] = _string(security)
    elif protocol == "vless":
        details["uuid"] = _string(data.get("uuid"))
        if "flow" in data:
            details["flow"] = _string(data.get("flow"))
        details["encryption"] = _string(data.get("encryption") or "none")
        if isinstance(data.get("reality-opts"), dict):
            details["security"] = "reality"
        elif data.get("security"):
            details["security"] = _string(data.get("security"))
        elif _bool(data.get("tls")):
            details["security"] = "tls"
        else:
            details["security"] = "none"
    elif protocol == "trojan":
        details["password"] = _string(data.get("password"))
        if data.get("security"):
            details["security"] = _string(data.get("security"))
        elif _bool(data.get("tls")):
            details["security"] = "tls"
    return details


def parse_clash_json(config: str) -> Optional[Proxy]:
    """Parse a single Clash proxy entry serialized as JSON."""
    try:
        config = config.strip()
        # Enforce MAX_CONFIG_LINE_LENGTH
        if MAX_CONFIG_LINE_LENGTH > 0 and len(config) > MAX_CONFIG_LINE_LENGTH:
            return None

        data = json.loads(config)
        if not isinstance(data, dict):
            return None

        # Check for mandatory Clash fields
        if "name" not in data or "type" not in data or "server" not in data:
            return None

        # Map to Proxy model
        protocol = data["type"].lower()
        address = data["server"]
        port = int(data.get("port", 0))
        if not (1 <= port <= 65535):
            return None
        uuid = data.get("uuid") or data.get("password") or ""

        # Basic mapping
        if protocol == "vmess":
            uuid = data.get("uuid", "")
            if not uuid:
                return None
        elif protocol == "vless":
            uuid = data.get("uuid", "")
            if not uuid:
                return None
        elif protocol == "trojan":
            uuid = data.get("password", "")
            if not uuid:
                return None
        elif protocol == "ss" or protocol == "shadowsocks":
            protocol = "shadowsocks"
            uuid = ""  # SS uses password in details
            password = data.get("password", "")
            if not password:
                # Reject Shadowsocks without password immediately
                return None
            method = str(data.get("method") or data.get("cipher", "")).lower()
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
            if method in invalid_methods or len(method) < 2:
                return None
        elif protocol == "wireguard" or protocol == "wg":
            protocol = "wireguard"
            # Enforce private_key for WireGuard (accept common aliases)
            private_key = (
                data.get("private_key")
                or data.get("private-key")
                or data.get("privateKey")
            )
            if not private_key:
                logger.debug(
                    "Dropping WireGuard proxy missing private_key: %s",
                    SecurityValidator.sanitize_log_message(address),
                )
                return None
        else:
            return None

        proxy = Proxy(
            config=config,  # Store the JSON blob as config
            protocol=protocol,
            address=address,
            port=port,
            uuid=uuid,
            details=_canonical_details(data, protocol),
            remarks=data.get("name", ""),
        )
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
        logger.debug(
            "Failed to parse Clash JSON: %s",
            SecurityValidator.sanitize_log_message(str(e)),
        )
        return None
