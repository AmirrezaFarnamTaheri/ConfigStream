# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cross-client generation and structural validation contracts."""

from __future__ import annotations

import base64
import binascii
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

_URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*$")
_XRAY_BUILTIN_TAGS = {"direct", "block"}


def _string_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)]


def _clean_tag(value: Any, fallback: str) -> str:
    tag = str(value or fallback).strip()
    return tag or fallback


def _unique_tag(base: str, seen: set[str]) -> str:
    tag = base
    suffix = 2
    while tag in seen:
        tag = f"{base} #{suffix}"
        suffix += 1
    seen.add(tag)
    return tag


def _normalise_alpn(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _xray_stream_settings(outbound: dict[str, Any]) -> dict[str, Any] | None:
    transport = outbound.get("transport")
    transport_obj = transport if isinstance(transport, dict) else {}
    method_raw = str(
        transport_obj.get("type")
        or outbound.get("network")
        or outbound.get("net")
        or "raw"
    ).lower()
    method_map = {
        "tcp": "raw",
        "raw": "raw",
        "ws": "websocket",
        "websocket": "websocket",
        "grpc": "grpc",
        "httpupgrade": "httpupgrade",
        "http-upgrade": "httpupgrade",
        "h2": "xhttp",
        "http": "xhttp",
        "xhttp": "xhttp",
        "kcp": "mkcp",
        "mkcp": "mkcp",
    }
    method = method_map.get(method_raw, "raw")
    stream: dict[str, Any] = {"method": method}

    path = transport_obj.get("path") or outbound.get("path")
    host = transport_obj.get("host") or outbound.get("host")
    service_name = (
        transport_obj.get("service_name")
        or transport_obj.get("serviceName")
        or outbound.get("service_name")
        or outbound.get("serviceName")
    )
    if method == "websocket":
        settings: dict[str, Any] = {}
        if path:
            settings["path"] = str(path)
        if host:
            settings["host"] = str(host)
            settings["headers"] = {"Host": str(host)}
        stream["wsSettings"] = settings
    elif method == "grpc":
        stream["grpcSettings"] = {"serviceName": str(service_name or "")}
    elif method == "httpupgrade":
        settings = {}
        if path:
            settings["path"] = str(path)
        if host:
            settings["host"] = str(host)
        stream["httpupgradeSettings"] = settings
    elif method == "xhttp":
        settings = {}
        if path:
            settings["path"] = str(path)
        if host:
            settings["host"] = str(host)
        stream["xhttpSettings"] = settings
    elif method == "mkcp":
        stream["kcpSettings"] = {}
    else:
        stream["rawSettings"] = {"header": {"type": "none"}}

    tls = outbound.get("tls")
    tls_obj = tls if isinstance(tls, dict) else {}
    security = str(
        outbound.get("security")
        or tls_obj.get("security")
        or ("tls" if tls_obj.get("enabled") else "none")
    ).lower()
    reality = tls_obj.get("reality")
    reality_obj = reality if isinstance(reality, dict) else {}
    if reality_obj.get("enabled") or security == "reality":
        stream["security"] = "reality"
        stream["realitySettings"] = {
            "serverName": str(
                reality_obj.get("server_name")
                or tls_obj.get("server_name")
                or outbound.get("sni")
                or ""
            ),
            "fingerprint": str(
                reality_obj.get("fingerprint")
                or tls_obj.get("fingerprint")
                or outbound.get("fingerprint")
                or "chrome"
            ),
            "password": str(
                reality_obj.get("public_key")
                or outbound.get("public_key")
                or outbound.get("pbk")
                or ""
            ),
            "shortId": str(
                reality_obj.get("short_id") or outbound.get("short_id") or ""
            ),
        }
    elif security == "tls" or tls_obj.get("enabled"):
        stream["security"] = "tls"
        tls_settings: dict[str, Any] = {
            "serverName": str(tls_obj.get("server_name") or outbound.get("sni") or ""),
            "allowInsecure": bool(
                tls_obj.get("insecure")
                or outbound.get("allow_insecure")
                or outbound.get("allowInsecure")
            ),
        }
        alpn = _normalise_alpn(tls_obj.get("alpn") or outbound.get("alpn"))
        if alpn:
            tls_settings["alpn"] = alpn
        fingerprint = (
            tls_obj.get("fingerprint")
            or outbound.get("fingerprint")
            or outbound.get("fp")
        )
        if fingerprint:
            tls_settings["fingerprint"] = str(fingerprint)
        stream["tlsSettings"] = tls_settings
    else:
        stream["security"] = "none"

    return stream


def _xray_outbound(outbound: dict[str, Any], tag: str) -> dict[str, Any] | None:
    kind = str(outbound.get("type") or "").lower()
    address = outbound.get("server")
    try:
        port = int(outbound.get("server_port") or 0)
    except (TypeError, ValueError):
        return None
    result: dict[str, Any] = {"tag": tag}

    if kind in {"http", "socks", "socks5"}:
        result["protocol"] = "socks" if kind.startswith("socks") else "http"
        settings: dict[str, Any] = {"address": address, "port": port}
        username = outbound.get("username")
        if username:
            settings["user"] = str(username)
            settings["pass"] = str(outbound.get("password") or "")
        result["settings"] = settings
    elif kind in {"shadowsocks", "ss"}:
        result.update(
            {
                "protocol": "shadowsocks",
                "settings": {
                    "address": address,
                    "port": port,
                    "method": outbound.get("method"),
                    "password": outbound.get("password"),
                },
            }
        )
    elif kind == "trojan":
        result.update(
            {
                "protocol": "trojan",
                "settings": {
                    "address": address,
                    "port": port,
                    "password": outbound.get("password"),
                },
            }
        )
    elif kind == "vmess":
        result.update(
            {
                "protocol": "vmess",
                "settings": {
                    "address": address,
                    "port": port,
                    "id": outbound.get("uuid"),
                    "security": outbound.get("encryption")
                    or outbound.get("security")
                    or "auto",
                },
            }
        )
    elif kind == "vless":
        settings = {
            "address": address,
            "port": port,
            "id": outbound.get("uuid"),
            "encryption": outbound.get("encryption") or "none",
        }
        if outbound.get("flow"):
            settings["flow"] = outbound["flow"]
        result.update({"protocol": "vless", "settings": settings})
    elif kind == "wireguard":
        peers = outbound.get("peers") or []
        if not peers or not isinstance(peers[0], dict):
            return None
        peer = peers[0]
        peer_settings: dict[str, Any] = {
            "endpoint": f"{peer.get('address')}:{int(peer.get('port') or 0)}",
            "publicKey": peer.get("public_key"),
        }
        if peer.get("pre_shared_key"):
            peer_settings["preSharedKey"] = peer["pre_shared_key"]
        if peer.get("persistent_keepalive_interval") is not None:
            peer_settings["keepAlive"] = int(
                peer.get("persistent_keepalive_interval") or 0
            )
        allowed_ips = _string_list(peer.get("allowed_ips"))
        if allowed_ips:
            peer_settings["allowedIPs"] = allowed_ips
        settings = {
            "secretKey": outbound.get("private_key"),
            "address": _string_list(
                outbound.get("address") or outbound.get("local_address")
            ),
            "peers": [peer_settings],
            "noKernelTun": True,
            "mtu": int(outbound.get("mtu") or 1420),
        }
        if peer.get("reserved") is not None:
            settings["reserved"] = peer["reserved"]
        result.update({"protocol": "wireguard", "settings": settings})
    else:
        return None

    if kind != "wireguard":
        result["streamSettings"] = _xray_stream_settings(outbound)
    detour = outbound.get("detour")
    if detour:
        result["proxySettings"] = {
            "tag": str(detour),
            "transportLayer": True,
        }
    return result


def _candidate_from_record(record: dict[str, Any]) -> dict[str, Any]:
    protocol = str(record.get("protocol") or "unknown").lower()
    details_raw = record.get("details")
    details = details_raw if isinstance(details_raw, dict) else {}
    kind = {"socks5": "socks", "ss": "shadowsocks", "wg": "wireguard"}.get(
        protocol, protocol
    )
    candidate: dict[str, Any] = {
        "type": kind,
        "tag": record.get("remarks") or record.get("id"),
        "server": record.get("address"),
        "server_port": record.get("port"),
    }
    if kind in {"http", "socks"}:
        candidate["username"] = (
            record.get("uuid") or details.get("username") or details.get("user")
        )
        candidate["password"] = details.get("password")
    elif kind == "shadowsocks":
        candidate["method"] = details.get("method") or details.get("cipher")
        candidate["password"] = details.get("password") or record.get("uuid")
    elif kind == "trojan":
        candidate["password"] = details.get("password") or record.get("uuid")
    elif kind in {"vless", "vmess"}:
        candidate["uuid"] = record.get("uuid")
        candidate["flow"] = details.get("flow")
        candidate["encryption"] = details.get("encryption")
        candidate["security"] = details.get("scy") or details.get("cipher")
    elif kind == "wireguard":
        candidate.update(
            {
                "private_key": details.get("private_key"),
                "address": details.get("local_address") or details.get("address"),
                "mtu": details.get("mtu"),
                "peers": [
                    {
                        "address": record.get("address"),
                        "port": record.get("port"),
                        "public_key": details.get("peer_public_key"),
                        "pre_shared_key": details.get("pre_shared_key"),
                        "reserved": details.get("reserved"),
                        "allowed_ips": details.get("allowed_ips"),
                        "persistent_keepalive_interval": details.get(
                            "persistent_keepalive_interval"
                        ),
                    }
                ],
            }
        )
    else:
        return {}

    network = details.get("network") or details.get("net") or details.get("type")
    if network:
        candidate["transport"] = {
            "type": network,
            "path": details.get("path"),
            "host": details.get("host"),
            "service_name": details.get("serviceName") or details.get("service_name"),
        }
    security = str(details.get("security") or "").lower()
    tls_enabled = bool(details.get("tls")) or security in {"tls", "reality"}
    if tls_enabled:
        tls: dict[str, Any] = {
            "enabled": True,
            "server_name": details.get("sni"),
            "alpn": details.get("alpn"),
            "fingerprint": details.get("fp"),
            "insecure": details.get("allowInsecure") or details.get("skip_cert_verify"),
        }
        if security == "reality":
            tls["reality"] = {
                "enabled": True,
                "server_name": details.get("sni"),
                "fingerprint": details.get("fp"),
                "public_key": details.get("pbk"),
                "short_id": details.get("sid"),
            }
        candidate["tls"] = tls
    if details.get("detour"):
        candidate["detour"] = details["detour"]
    return candidate


def generate_xray_config(
    records: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Generate a modern Xray client config from public proxy records."""
    outbounds: list[dict[str, Any]] = []
    seen: set[str] = set()
    unsupported: Counter[str] = Counter()
    emitted_records = 0
    for record in records:
        if not record.get("is_working"):
            continue
        protocol = str(record.get("protocol") or "unknown").lower()
        candidates: list[dict[str, Any]] = []
        if protocol in {"chain", "revived"}:
            try:
                payload = json.loads(str(record.get("config") or ""))
            except json.JSONDecodeError:
                payload = {}
            if isinstance(payload, dict):
                for key in ("outbounds", "endpoints"):
                    values = payload.get(key, [])
                    if isinstance(values, list):
                        candidates.extend(
                            value for value in values if isinstance(value, dict)
                        )
        else:
            candidate = _candidate_from_record(record)
            if candidate:
                candidates.append(candidate)

        before = len(outbounds)
        for candidate in candidates:
            base = _clean_tag(candidate.get("tag"), f"{protocol}-{len(seen) + 1}")
            tag = _unique_tag(base, seen)
            converted = _xray_outbound(candidate, tag)
            if converted:
                outbounds.append(converted)
        if len(outbounds) == before:
            unsupported[protocol] += 1
        else:
            emitted_records += 1

    outbounds.extend(
        [
            {"tag": "direct", "protocol": "freedom", "settings": {}},
            {"tag": "block", "protocol": "blackhole", "settings": {}},
        ]
    )
    config = {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "tag": "socks-in",
                "listen": "127.0.0.1",
                "port": 10808,
                "protocol": "socks",
                "settings": {"udp": True},
            },
            {
                "tag": "http-in",
                "listen": "127.0.0.1",
                "port": 10809,
                "protocol": "http",
                "settings": {},
            },
        ],
        "outbounds": outbounds,
        "routing": {
            "domainStrategy": "AsIs",
            "rules": [
                {
                    "type": "field",
                    "ip": ["geoip:private"],
                    "outboundTag": "direct",
                },
                {
                    "type": "field",
                    "protocol": ["bittorrent"],
                    "outboundTag": "block",
                },
            ],
        },
    }
    report = {
        "status": "generated",
        "target": "Xray-core v26.3.27",
        "emitted_records": emitted_records,
        "outbound_count": len(outbounds),
        "unsupported": dict(unsupported),
    }
    return config, report


def validate_xray_config(payload: object, file_name: str = "xray.json") -> list[str]:
    """Validate Xray references and modern outbound shapes before native checks."""
    if not isinstance(payload, dict):
        return [f"{file_name} must be a JSON object"]
    outbounds = payload.get("outbounds")
    if not isinstance(outbounds, list) or not outbounds:
        return [f"{file_name} outbounds must be a non-empty list"]
    errors: list[str] = []
    tags: set[str] = set()
    references: list[tuple[str, str]] = []
    for index, outbound in enumerate(outbounds):
        if not isinstance(outbound, dict):
            errors.append(f"{file_name} outbounds[{index}] must be an object")
            continue
        tag = outbound.get("tag")
        protocol = outbound.get("protocol")
        settings = outbound.get("settings")
        if not isinstance(tag, str) or not tag:
            errors.append(f"{file_name} outbounds[{index}] missing tag")
        elif tag in tags:
            errors.append(f"{file_name} duplicate outbound tag: {tag}")
        else:
            tags.add(tag)
        if not isinstance(protocol, str) or not protocol:
            errors.append(f"{file_name} outbounds[{index}] missing protocol")
        if not isinstance(settings, dict):
            errors.append(f"{file_name} outbounds[{index}] settings must be an object")
            continue
        if protocol in {"vmess", "vless"}:
            if "vnext" in settings:
                errors.append(
                    f"{file_name} outbounds[{index}] uses obsolete vnext settings"
                )
            for key in ("address", "port", "id"):
                if settings.get(key) in (None, ""):
                    errors.append(
                        f"{file_name} outbounds[{index}] missing modern {protocol} {key}"
                    )
        proxy_settings = outbound.get("proxySettings")
        if isinstance(proxy_settings, dict) and proxy_settings.get("tag"):
            references.append(
                (
                    f"outbounds[{index}].proxySettings.tag",
                    str(proxy_settings["tag"]),
                )
            )
        stream_settings = outbound.get("streamSettings")
        if stream_settings is not None and not isinstance(stream_settings, dict):
            errors.append(
                f"{file_name} outbounds[{index}] streamSettings must be an object"
            )

    routing = payload.get("routing")
    if isinstance(routing, dict):
        rules = routing.get("rules")
        if isinstance(rules, list):
            for index, rule in enumerate(rules):
                if isinstance(rule, dict) and rule.get("outboundTag"):
                    references.append(
                        (
                            f"routing.rules[{index}].outboundTag",
                            str(rule["outboundTag"]),
                        )
                    )
    for location, reference in references:
        if reference not in tags and reference not in _XRAY_BUILTIN_TAGS:
            errors.append(f"{file_name} {location} references unknown tag: {reference}")
    return errors


def validate_mihomo_config(payload: object, file_name: str) -> list[str]:
    """Validate Mihomo-specific references omitted by generic Clash checks."""
    if not isinstance(payload, dict):
        return []
    errors: list[str] = []
    names = {"DIRECT", "REJECT", "GLOBAL"}
    proxies = payload.get("proxies")
    groups = payload.get("proxy-groups")
    if isinstance(proxies, list):
        names.update(
            str(item.get("name"))
            for item in proxies
            if isinstance(item, dict) and item.get("name")
        )
    if isinstance(groups, list):
        names.update(
            str(item.get("name"))
            for item in groups
            if isinstance(item, dict) and item.get("name")
        )
        for index, group in enumerate(groups):
            if isinstance(group, dict) and group.get("type") == "relay":
                errors.append(
                    f"{file_name} proxy-groups[{index}] uses deprecated relay type"
                )
    if isinstance(proxies, list):
        for index, proxy in enumerate(proxies):
            if not isinstance(proxy, dict):
                continue
            dialer = proxy.get("dialer-proxy")
            if dialer is not None:
                if not isinstance(dialer, str) or not dialer:
                    errors.append(
                        f"{file_name} proxies[{index}] has invalid dialer-proxy"
                    )
                elif dialer not in names:
                    errors.append(
                        f"{file_name} proxies[{index}] unknown dialer-proxy: {dialer}"
                    )
            if proxy.get("type") == "wireguard":
                for key in ("server", "port", "ip", "private-key", "public-key"):
                    if proxy.get(key) in (None, ""):
                        errors.append(
                            f"{file_name} proxies[{index}] wireguard missing {key}"
                        )
    return errors


def validate_nekobox_subscriptions(root: Path) -> list[str]:
    """Validate share-link/Base64 subscriptions consumed by NekoBox/v2rayN."""
    errors: list[str] = []
    pairs = (
        ("proxies.txt", "base64.txt"),
        ("proxies-dns-safe.txt", "base64-dns-safe.txt"),
        ("proxies-dns-hardened.txt", "base64-dns-hardened.txt"),
    )
    for text_name, base64_name in pairs:
        text_path = root / text_name
        encoded_path = root / base64_name
        if not text_path.is_file() or not encoded_path.is_file():
            continue
        try:
            text = text_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{text_name} is not valid UTF-8: {exc}")
            continue
        try:
            encoded = encoded_path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{base64_name} is not valid UTF-8: {exc}")
            continue
        try:
            decoded = (
                base64.b64decode(encoded, validate=True).decode("utf-8")
                if encoded
                else ""
            )
        except (binascii.Error, UnicodeDecodeError) as exc:
            errors.append(f"{base64_name} is not valid Base64 UTF-8: {exc}")
            continue
        if decoded != text:
            errors.append(f"{base64_name} does not decode exactly to {text_name}")
        for index, line in enumerate(text.splitlines(), start=1):
            value = line.strip()
            if not value:
                continue
            if any(ord(char) < 32 for char in value):
                errors.append(f"{text_name} line {index} contains control characters")
                continue
            parsed = urlsplit(value)
            if not parsed.scheme or not _URI_SCHEME_RE.match(parsed.scheme):
                errors.append(f"{text_name} line {index} is not a valid share link")
    return errors
