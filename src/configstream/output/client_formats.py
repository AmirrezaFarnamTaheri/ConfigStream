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

from ..converters import to_singbox_outbound
from ..converters.singbox import wireguard_outbound_to_endpoint
from ..models import Proxy
from .xray_security import transport_security_error

_URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*$")
_XRAY_BUILTIN_TAGS = {"direct", "block"}
_XRAY_STREAM_METHOD_SETTINGS = {
    "raw": "rawSettings",
    "websocket": "wsSettings",
    "grpc": "grpcSettings",
    "httpupgrade": "httpupgradeSettings",
    "xhttp": "xhttpSettings",
    "mkcp": "kcpSettings",
}
_XRAY_GENERATED_PROXY_PROTOCOLS = {
    "http",
    "socks",
    "shadowsocks",
    "trojan",
    "vmess",
    "vless",
}
_NEKOBOX_HELPER_TYPES = {"selector", "urltest", "direct", "block", "dns"}


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
        # NOTE: no allowInsecure here - Xray >= 26.7 removed the feature and
        # refuses to load any config that still carries the field, which
        # would make xray.json unusable for every proxy because of one hop.
        tls_settings: dict[str, Any] = {
            "serverName": str(tls_obj.get("server_name") or outbound.get("sni") or ""),
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
    if kind != "wireguard" and (
        not isinstance(address, str) or not address.strip() or not 1 <= port <= 65535
    ):
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
        if not outbound.get("method") or not outbound.get("password"):
            return None
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
        try:
            normalized = wireguard_outbound_to_endpoint(
                {
                    "type": "wireguard",
                    "tag": tag,
                    "address": outbound.get("address") or outbound.get("local_address"),
                    "private_key": outbound.get("private_key"),
                    "mtu": outbound.get("mtu"),
                    "peers": outbound.get("peers"),
                }
            )
        except (TypeError, ValueError):
            return None

        peer_settings: list[dict[str, Any]] = []
        peers = normalized["peers"]
        for peer in peers:
            peer_host = str(peer["address"]).strip().strip("[]")
            endpoint_host = f"[{peer_host}]" if ":" in peer_host else peer_host
            rendered_peer: dict[str, Any] = {
                "endpoint": f"{endpoint_host}:{peer['port']}",
                "publicKey": peer["public_key"],
            }
            if peer.get("pre_shared_key"):
                rendered_peer["preSharedKey"] = peer["pre_shared_key"]
            if peer.get("persistent_keepalive_interval") is not None:
                rendered_peer["keepAlive"] = peer["persistent_keepalive_interval"]
            allowed_ips = _string_list(peer.get("allowed_ips"))
            if allowed_ips:
                rendered_peer["allowedIPs"] = allowed_ips
            peer_settings.append(rendered_peer)

        reserved_values = [peer.get("reserved") for peer in peers]
        if any(value is not None for value in reserved_values) and any(
            value != reserved_values[0] for value in reserved_values[1:]
        ):
            return None
        settings = {
            "secretKey": normalized["private_key"],
            "address": normalized["address"],
            "peers": peer_settings,
            "noKernelTun": True,
            "mtu": int(normalized.get("mtu") or 1420),
        }
        if reserved_values and reserved_values[0] is not None:
            settings["reserved"] = reserved_values[0]
        result.update({"protocol": "wireguard", "settings": settings})
    else:
        return None

    if kind != "wireguard":
        result["streamSettings"] = _xray_stream_settings(outbound)
    stream = result.get("streamSettings") or {}
    if transport_security_error(result["protocol"], result["settings"], stream):
        return None
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

        tag_map: dict[str, str] = {}
        pending: list[tuple[dict[str, Any], str]] = []
        for candidate in candidates:
            original = str(candidate.get("tag") or "")
            base = _clean_tag(candidate.get("tag"), f"{protocol}-{len(seen) + 1}")
            if base in _XRAY_BUILTIN_TAGS:
                base = f"proxy-{base}"
            tag = base
            suffix = 2
            while tag in seen or any(item[1] == tag for item in pending):
                tag = f"{base}-{suffix}"
                suffix += 1
            pending.append((candidate, tag))
            if original:
                tag_map[original] = tag
        converted_batch: list[dict[str, Any]] = []
        for candidate, tag in pending:
            detour = candidate.get("detour")
            if detour and str(detour) in tag_map:
                candidate = {**candidate, "detour": tag_map[str(detour)]}
            converted = _xray_outbound(candidate, tag)
            if converted:
                converted_batch.append(converted)
        batch_tags = {item["tag"] for item in converted_batch} | _XRAY_BUILTIN_TAGS
        missing_detour = any(
            item.get("proxySettings", {}).get("tag", "direct") not in batch_tags
            for item in converted_batch
        )
        # A partially converted chain changes routing or leaves dangling hops.
        if (
            not converted_batch
            or len(converted_batch) != len(pending)
            or missing_detour
        ):
            unsupported[protocol] += 1
        else:
            outbounds.extend(converted_batch)
            seen.update(item["tag"] for item in converted_batch)
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
        "target": "Xray-core v26.7.28",
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
            continue
        if not isinstance(settings, dict):
            errors.append(f"{file_name} outbounds[{index}] settings must be an object")
            continue
        if protocol in _XRAY_GENERATED_PROXY_PROTOCOLS:
            address = settings.get("address")
            if not isinstance(address, str) or not address.strip():
                errors.append(
                    f"{file_name} outbounds[{index}] missing modern {protocol} address"
                )
            port = settings.get("port")
            if (
                not isinstance(port, int)
                or isinstance(port, bool)
                or not 1 <= port <= 65535
            ):
                errors.append(
                    f"{file_name} outbounds[{index}] missing modern {protocol} port"
                )
        if protocol in {"vmess", "vless"}:
            if "vnext" in settings:
                errors.append(
                    f"{file_name} outbounds[{index}] uses obsolete vnext settings"
                )
            identifier = settings.get("id")
            if not isinstance(identifier, str) or not identifier.strip():
                errors.append(
                    f"{file_name} outbounds[{index}] missing modern {protocol} id"
                )
        if protocol in {"trojan", "shadowsocks"}:
            password = settings.get("password")
            if not isinstance(password, str) or not password:
                errors.append(
                    f"{file_name} outbounds[{index}] missing {protocol} password"
                )
        if protocol == "shadowsocks":
            method = settings.get("method")
            if not isinstance(method, str) or not method.strip():
                errors.append(
                    f"{file_name} outbounds[{index}] missing shadowsocks method"
                )
        if protocol == "wireguard":
            secret_key = settings.get("secretKey")
            if not isinstance(secret_key, str) or not secret_key:
                errors.append(
                    f"{file_name} outbounds[{index}] missing wireguard secretKey"
                )
            addresses = settings.get("address")
            if (
                not isinstance(addresses, list)
                or not addresses
                or not all(
                    isinstance(item, str) and bool(item.strip()) for item in addresses
                )
            ):
                errors.append(
                    f"{file_name} outbounds[{index}] wireguard address must be a non-empty string list"
                )
            peers = settings.get("peers")
            if not isinstance(peers, list) or not peers:
                errors.append(
                    f"{file_name} outbounds[{index}] wireguard peers must be a non-empty list"
                )
            else:
                for peer_index, peer in enumerate(peers):
                    if not isinstance(peer, dict):
                        errors.append(
                            f"{file_name} outbounds[{index}] wireguard peers[{peer_index}] must be an object"
                        )
                        continue
                    endpoint = peer.get("endpoint")
                    if not isinstance(endpoint, str) or not endpoint.strip():
                        errors.append(
                            f"{file_name} outbounds[{index}] wireguard peers[{peer_index}] missing endpoint"
                        )
                    public_key = peer.get("publicKey")
                    if not isinstance(public_key, str) or not public_key:
                        errors.append(
                            f"{file_name} outbounds[{index}] wireguard peers[{peer_index}] missing publicKey"
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
        if protocol in _XRAY_GENERATED_PROXY_PROTOCOLS and not isinstance(
            stream_settings, dict
        ):
            errors.append(f"{file_name} outbounds[{index}] missing streamSettings")
        elif stream_settings is not None and not isinstance(stream_settings, dict):
            errors.append(
                f"{file_name} outbounds[{index}] streamSettings must be an object"
            )
        elif isinstance(stream_settings, dict):
            security_error = transport_security_error(
                str(protocol), settings, stream_settings
            )
            if security_error:
                errors.append(f"{file_name} outbounds[{index}] {security_error}")
            stream_method = stream_settings.get("method")
            if (
                not isinstance(stream_method, str)
                or stream_method not in _XRAY_STREAM_METHOD_SETTINGS
            ):
                errors.append(
                    f"{file_name} outbounds[{index}] has invalid streamSettings.method"
                )
            else:
                expected_key = _XRAY_STREAM_METHOD_SETTINGS[str(stream_method)]
                if not isinstance(stream_settings.get(expected_key), dict):
                    errors.append(
                        f"{file_name} outbounds[{index}] method {stream_method} requires {expected_key}"
                    )
                for method_key in set(_XRAY_STREAM_METHOD_SETTINGS.values()) - {
                    expected_key
                }:
                    if method_key in stream_settings:
                        errors.append(
                            f"{file_name} outbounds[{index}] method {stream_method} conflicts with {method_key}"
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


def generate_nekobox_json_subscription(proxies: list[Proxy]) -> str:
    """Render NekoBox's multi-node JSON subscription container.

    NekoBox treats a complete sing-box JSON document with routing, DNS, or
    inbounds as one custom/profile configuration. Its subscription updater
    expands the `outbounds` and `endpoints` arrays of a minimal JSON object
    into separate nodes. Keep dependency-bearing/helper entries out of this
    surface so every emitted node remains independently importable.
    """

    outbounds: list[dict[str, Any]] = []
    endpoints: list[dict[str, Any]] = []
    seen_tags: set[str] = set()
    for proxy in proxies:
        try:
            converted = to_singbox_outbound(proxy)
        except (AttributeError, KeyError, TypeError, ValueError):
            continue
        if not isinstance(converted, dict):
            continue

        # Extra outbounds make the primary node dependency-bearing. Flattening
        # them would silently change routing semantics, so omit that record.
        if converted.get("_extra_outbounds"):
            continue

        outbound = {
            str(key): value
            for key, value in converted.items()
            if not str(key).startswith("_")
        }
        kind = str(outbound.get("type") or "").strip().lower()
        if not kind or kind in _NEKOBOX_HELPER_TYPES:
            continue
        if outbound.get("detour") not in (None, ""):
            continue

        fallback = proxy.remarks or str(proxy.id or "") or f"{kind}-node"
        base_tag = _clean_tag(outbound.get("tag"), fallback)
        outbound["tag"] = _unique_tag(base_tag, seen_tags)

        if kind == "wireguard":
            try:
                endpoint = wireguard_outbound_to_endpoint(outbound)
            except (TypeError, ValueError):
                continue
            if endpoint.get("detour") not in (None, ""):
                continue
            endpoints.append(endpoint)
        else:
            outbounds.append(outbound)

    payload = {"outbounds": outbounds, "endpoints": endpoints}
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def validate_nekobox_json_subscription(
    payload: object, file_name: str = "nekobox.json"
) -> list[str]:
    """Validate NekoBox's minimal multi-node JSON subscription container."""

    if not isinstance(payload, dict):
        return [
            f"{file_name} must be a JSON object containing outbounds/endpoints arrays"
        ]

    errors: list[str] = []
    allowed_keys = {"outbounds", "endpoints"}
    unexpected = sorted(str(key) for key in payload if key not in allowed_keys)
    if unexpected:
        errors.append(
            f"{file_name} contains profile-level/unsupported top-level keys: "
            + ", ".join(unexpected)
        )
    if not any(key in payload for key in allowed_keys):
        errors.append(f"{file_name} must define outbounds and/or endpoints arrays")

    seen_tags: set[str] = set()
    for collection in ("outbounds", "endpoints"):
        items = payload.get(collection, [])
        if not isinstance(items, list):
            errors.append(f"{file_name}.{collection} must be a JSON array")
            continue
        for index, item in enumerate(items):
            location = f"{file_name}.{collection}[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{location} must be a node object")
                continue
            kind = str(item.get("type") or "").strip().lower()
            if not kind:
                errors.append(f"{location} missing node type")
            elif kind in _NEKOBOX_HELPER_TYPES:
                errors.append(
                    f"{location} uses helper type {kind}; "
                    "multi-node subscriptions must contain standalone nodes"
                )
            if collection == "outbounds" and kind == "wireguard":
                errors.append(
                    f"{location} uses legacy WireGuard outbound shape; "
                    "sing-box 1.13+ WireGuard nodes must be under endpoints"
                )

            tag = item.get("tag")
            if not isinstance(tag, str) or not tag.strip():
                errors.append(f"{location} missing non-empty tag")
            elif tag in seen_tags:
                errors.append(f"{location} duplicates tag: {tag}")
            else:
                seen_tags.add(tag)

            if item.get("detour") not in (None, ""):
                errors.append(
                    f"{location} has detour; NekoBox multi-node items "
                    "must be independently importable"
                )
            if any(str(key).startswith("_") for key in item):
                errors.append(f"{location} contains private ConfigStream metadata")

    return errors


def validate_nekobox_subscriptions(root: Path) -> list[str]:
    """Validate share-link/Base64 subscriptions consumed by NekoBox/v2rayN."""
    errors: list[str] = []
    pairs = (
        ("proxies.txt", "base64.txt"),
        ("proxies-dns-safe.txt", "base64-dns-safe.txt"),
        ("proxies-dns-hardened.txt", "base64-dns-hardened.txt"),
    )
    json_names = (
        "nekobox.json",
        "nekobox-dns-safe.json",
        "nekobox-dns-hardened.json",
        "chosen/nekobox.json",
        "chosen/nekobox-dns-safe.json",
        "chosen/nekobox-dns-hardened.json",
    )
    for json_name in json_names:
        path = root / json_name
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"{json_name} is not valid UTF-8 JSON: {exc}")
            continue
        errors.extend(validate_nekobox_json_subscription(payload, json_name))

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
