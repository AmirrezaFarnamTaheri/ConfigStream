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


_DETAILS_KEYS = {
    "vmess": frozenset({
        "uuid", "aid", "alterId", "security", "sni", "path", "host", "type",
        "net", "serviceName", "grpc_service_name", "http_host", "ws_host",
        "http_path", "ws_path", "fp", "fingerprint", "server_name", "alpn",
        "tls", "allowInsecure", "skip_cert_verify", "detour", "tag",
        "has_utls", "has_alpn_rotation", "has_multiplexing",
    }),
    "vless": frozenset({
        "uuid", "security", "encryption", "flow", "sni", "path", "host",
        "type", "net", "serviceName", "grpc_service_name", "http_host",
        "ws_host", "http_path", "ws_path", "fp", "fingerprint", "server_name",
        "alpn", "tls", "allowInsecure", "skip_cert_verify", "pbk", "publicKey",
        "shortId", "short_id", "sid", "original_host", "resolved_ip", "detour",
        "tag", "has_utls", "has_alpn_rotation", "has_multiplexing",
    }),
    "trojan": frozenset({
        "password", "uuid", "security", "sni", "path", "host", "type", "net",
        "serviceName", "grpc_service_name", "alpn", "tls", "allowInsecure",
        "skip_cert_verify", "detour", "tag", "has_utls",
        "has_alpn_rotation", "has_multiplexing",
    }),
    "shadowsocks": frozenset({
        "method", "password", "plugin", "plugin_opts", "obfs", "obfs_param",
        "protocol", "protocol_param", "server", "port", "udp_over_tcp", "detour",
        "tag", "has_utls", "has_alpn_rotation", "has_multiplexing",
    }),
    "wireguard": frozenset({
        "private_key", "peer_public_key", "public_key", "pre_shared_key",
        "presharedKey", "reserved", "mtu", "local_address", "private_ipv4",
        "private_ipv6", "server", "server_port", "detour", "tag", "has_utls",
        "has_alpn_rotation", "has_multiplexing",
    }),
}


def _canonical_clash_details(data: dict, protocol: str, address: str, port: int) -> dict:
    """Map Clash-only field names into the closed canonical details schema."""

    details = dict(data)
    if "skip-cert-verify" in details and "skip_cert_verify" not in details:
        details["skip_cert_verify"] = bool(details["skip-cert-verify"])
    if "server-name" in details and "server_name" not in details:
        details["server_name"] = details["server-name"]
    if "servername" in details and "sni" not in details:
        details["sni"] = details["servername"]
    if "network" in details and "net" not in details:
        details["net"] = details["network"]
    if "client-fingerprint" in details and "fp" not in details:
        details["fp"] = details["client-fingerprint"]

    ws_opts = details.get("ws-opts")
    if isinstance(ws_opts, dict):
        if ws_opts.get("path") and not details.get("path"):
            details["path"] = ws_opts["path"]
        headers = ws_opts.get("headers")
        if isinstance(headers, dict) and headers.get("Host") and not details.get("host"):
            details["host"] = headers["Host"]

    grpc_opts = details.get("grpc-opts")
    if isinstance(grpc_opts, dict):
        service_name = grpc_opts.get("grpc-service-name") or grpc_opts.get("service-name")
        if service_name and not details.get("serviceName"):
            details["serviceName"] = service_name

    reality_opts = details.get("reality-opts")
    if isinstance(reality_opts, dict):
        if reality_opts.get("public-key") and not details.get("pbk"):
            details["pbk"] = reality_opts["public-key"]
        if reality_opts.get("short-id") and not details.get("sid"):
            details["sid"] = reality_opts["short-id"]

    if protocol == "shadowsocks":
        details["method"] = details.get("method") or details.get("cipher", "")
        details["server"] = address
        details["port"] = port
        if "plugin-opts" in details and "plugin_opts" not in details:
            details["plugin_opts"] = details["plugin-opts"]
    elif protocol == "wireguard":
        aliases = {
            "private-key": "private_key",
            "privateKey": "private_key",
            "public-key": "peer_public_key",
            "peer-public-key": "peer_public_key",
            "preshared-key": "pre_shared_key",
            "pre-shared-key": "pre_shared_key",
        }
        for source_key, target_key in aliases.items():
            if details.get(source_key) and not details.get(target_key):
                details[target_key] = details[source_key]
        if details.get("ip") and not details.get("local_address"):
            details["local_address"] = details["ip"]
        details["server"] = address
        details["server_port"] = port

    allowed = _DETAILS_KEYS[protocol]
    return {key: value for key, value in details.items() if key in allowed}


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
            data["password"] = password
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
            if not (
                data.get("private_key")
                or data.get("private-key")
                or data.get("privateKey")
            ):
                logger.debug(
                    "Dropping WireGuard proxy missing private_key: %s",
                    SecurityValidator.sanitize_log_message(address),
                )
                return None
        else:
            return None

        details = _canonical_clash_details(data, protocol, address, port)
        proxy = Proxy(
            config=config,  # Store the JSON blob as config
            protocol=protocol,
            address=address,
            port=port,
            uuid=uuid,
            details=details,
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
