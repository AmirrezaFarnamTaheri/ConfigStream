# SPDX-License-Identifier: AGPL-3.0-or-later
"""Structural validation for modern Sing-box full configurations."""

from __future__ import annotations

from typing import Any


def _collect_tagged_items(
    payload: dict[str, Any], file_name: str, errors: list[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]:
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

    tags: set[str] = set()
    outbounds: list[dict[str, Any]] = []
    endpoints: list[dict[str, Any]] = []
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
    item: dict[str, Any],
    location: str,
    tags: set[str],
    errors: list[str],
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


def validate_singbox_config(payload: object, file_name: str) -> list[str]:
    """Validate tags and references across Sing-box outbounds and endpoints."""
    if not isinstance(payload, dict):
        return [f"{file_name} must be a JSON object"]

    errors: list[str] = []
    outbounds, endpoints, tags = _collect_tagged_items(payload, file_name, errors)

    for index, endpoint in enumerate(endpoints):
        _validate_detour(
            endpoint,
            f"{file_name} endpoints[{index}]",
            tags,
            errors,
            file_name=file_name,
            item_kind="endpoint",
        )

    for index, outbound in enumerate(outbounds):
        _validate_detour(
            outbound,
            f"{file_name} outbounds[{index}]",
            tags,
            errors,
            file_name=file_name,
            item_kind="outbound",
        )
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

    route = payload.get("route")
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
                if detour is None:
                    continue
                if not isinstance(detour, str) or not detour:
                    errors.append(
                        f"{file_name} dns.servers[{index}] has invalid detour"
                    )
                elif detour not in tags:
                    errors.append(f"{file_name} unknown DNS detour: {detour}")
    return errors
