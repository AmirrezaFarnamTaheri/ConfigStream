# SPDX-License-Identifier: AGPL-3.0-or-later
"""Structural validation for modern Sing-box full configurations."""

from __future__ import annotations

import ipaddress
from typing import Any, Dict, List, Set, Tuple


def _collect_tagged_items(
    payload: Dict[str, Any], file_name: str, errors: List[str]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Set[str]]:
    outbounds_raw = payload.get("outbounds")
    if not isinstance(outbounds_raw, list) or not outbounds_raw:
        errors.append(f"{file_name} outbounds must be a non-empty list")
        outbounds_raw = []

    endpoints_raw = payload.get("endpoints", [])
    if endpoints_raw is None:
        endpoints_raw = []
    if not isinstance(endpoints_raw, list):
        errors.append(f"{file_name} endpoints must be a list")
        endpoints_raw = []

    tags: Set[str] = set()
    outbounds: List[Dict[str, Any]] = []
    endpoints: List[Dict[str, Any]] = []
    for collection_name, values, target in (
        ("outbounds", outbounds_raw, outbounds),
        ("endpoints", endpoints_raw, endpoints),
    ):
        for index, item in enumerate(values):
            if not isinstance(item, dict):
                errors.append(
                    f"{file_name} {collection_name}[{index}] must be an object"
                )
                continue
            target.append(item)
            item_type = item.get("type")
            tag = item.get("tag")
            if not isinstance(item_type, str) or not item_type:
                errors.append(f"{file_name} {collection_name}[{index}] missing type")
            if not isinstance(tag, str) or not tag:
                errors.append(f"{file_name} {collection_name}[{index}] missing tag")
                continue
            if tag in tags:
                errors.append(f"{file_name} duplicate outbound/endpoint tag: {tag}")
            tags.add(tag)
    return outbounds, endpoints, tags


def _validate_detour(
    item: Dict[str, Any],
    location: str,
    tags: Set[str],
    errors: List[str],
    file_name: str = "",
    item_kind: str = "outbound",
) -> None:
    detour = item.get("detour")
    if detour is None:
        return
    if not isinstance(detour, str) or not detour:
        errors.append(f"{location} has invalid detour")
    elif detour not in tags:
        errors.append(f"{file_name} unknown {item_kind} detour: {detour}")


def _is_hostname(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    host = value.strip().strip("[]")
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        return True


def _resolver_server(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, dict):
        server = value.get("server")
        if isinstance(server, str) and server:
            return server
    return None


def _dns_server_tags(payload: Dict[str, Any]) -> Set[str]:
    dns = payload.get("dns")
    if not isinstance(dns, dict):
        return set()
    servers = dns.get("servers")
    if not isinstance(servers, list):
        return set()
    return {
        str(server.get("tag"))
        for server in servers
        if isinstance(server, dict) and server.get("tag")
    }


def validate_singbox_config(payload: object, file_name: str) -> List[str]:
    """Validate tags, references, and hostname-resolution contracts."""
    if not isinstance(payload, dict):
        return [f"{file_name} must be a JSON object"]

    errors: List[str] = []
    outbounds, endpoints, tags = _collect_tagged_items(payload, file_name, errors)
    dns_tags = _dns_server_tags(payload)

    route = payload.get("route")
    default_domain_resolver: str | None = None
    if isinstance(route, dict):
        resolver = route.get("default_domain_resolver")
        if resolver is not None:
            resolver_tag = _resolver_server(resolver)
            if resolver_tag is None:
                errors.append(
                    f"{file_name} route.default_domain_resolver must reference a DNS server"
                )
            elif resolver_tag not in dns_tags:
                errors.append(
                    f"{file_name} unknown route default domain resolver: {resolver_tag}"
                )
            else:
                default_domain_resolver = resolver_tag

    for collection_name, values in (("endpoints", endpoints), ("outbounds", outbounds)):
        for index, item in enumerate(values):
            _validate_detour(
                item,
                f"{file_name} {collection_name}[{index}]",
                tags,
                errors,
                file_name=file_name,
                item_kind=collection_name[:-1],
            )
            needs_domain_resolver = item.get("type") == "direct" or _is_hostname(
                item.get("server")
            )
            if needs_domain_resolver:
                resolver = (
                    _resolver_server(item.get("domain_resolver"))
                    or default_domain_resolver
                )
                if resolver is None and len(dns_tags) > 1:
                    errors.append(
                        f"{file_name} {collection_name}[{index}] domain dial lacks domain resolver"
                    )
                elif resolver is not None and resolver not in dns_tags:
                    errors.append(
                        f"{file_name} {collection_name}[{index}] unknown domain resolver: {resolver}"
                    )

    for index, outbound in enumerate(outbounds):
        if outbound.get("type") not in {"selector", "urltest"}:
            continue
        refs = outbound.get("outbounds")
        if not isinstance(refs, list) or not refs:
            errors.append(f"{file_name} outbounds[{index}] missing outbound references")
            continue
        for ref in refs:
            if not isinstance(ref, str) or not ref:
                errors.append(f"{file_name} outbounds[{index}] has invalid reference")
            elif ref not in tags:
                errors.append(f"{file_name} unknown outbound reference: {ref}")

    if isinstance(route, dict):
        final = route.get("final")
        if final is not None:
            if not isinstance(final, str) or not final:
                errors.append(f"{file_name} route.final must be a non-empty string")
            elif final not in tags:
                errors.append(f"{file_name} unknown route final: {final}")
        rules = route.get("rules")
        if isinstance(rules, list):
            for index, rule in enumerate(rules):
                if not isinstance(rule, dict):
                    continue
                ref = rule.get("outbound")
                if ref is None:
                    continue
                if not isinstance(ref, str) or not ref:
                    errors.append(
                        f"{file_name} route.rules[{index}] has invalid outbound"
                    )
                elif ref not in tags:
                    errors.append(f"{file_name} unknown route outbound: {ref}")

    dns = payload.get("dns")
    if isinstance(dns, dict):
        servers = dns.get("servers")
        if isinstance(servers, list):
            for index, server in enumerate(servers):
                if not isinstance(server, dict):
                    continue
                detour = server.get("detour")
                if detour is not None:
                    if not isinstance(detour, str) or not detour:
                        errors.append(
                            f"{file_name} dns.servers[{index}] has invalid detour"
                        )
                    elif detour not in tags:
                        errors.append(f"{file_name} unknown DNS detour: {detour}")
                if _is_hostname(server.get("server")):
                    resolver = _resolver_server(server.get("domain_resolver"))
                    if resolver is None:
                        errors.append(
                            f"{file_name} dns.servers[{index}] hostname server lacks domain_resolver"
                        )
                    elif resolver not in dns_tags:
                        errors.append(
                            f"{file_name} dns.servers[{index}] unknown domain_resolver: {resolver}"
                        )
    return errors
