"""Proxy deduplication helpers."""

from __future__ import annotations

from typing import Any, Iterable, List, Tuple

from .models import Proxy


def proxy_key(proxy: Proxy) -> Tuple[Any, ...]:
    """Generate a stable key representing the proxy endpoint semantics."""

    return (
        proxy.scheme.lower(),
        proxy.host.lower(),
        int(proxy.port),
        (proxy.user or proxy.uuid or "").lower(),
        (proxy.sni or "").lower(),
        tuple(sorted(a.lower() for a in proxy.alpn or ())),
        proxy.path or "/",
    )


def dedupe_keep_best(proxies: Iterable[Proxy]) -> List[Proxy]:
    """Deduplicate proxies, keeping the copy with the best measured quality."""

    best: dict[Tuple[Any, ...], Proxy] = {}

    for proxy in proxies:
        key = proxy_key(proxy)
        current = best.get(key)
        if current is None:
            best[key] = proxy
            continue

        candidate_latency = proxy.latency_ms
        current_latency = current.latency_ms

        if candidate_latency is not None:
            if current_latency is None or candidate_latency < current_latency:
                best[key] = proxy
                continue

        if not getattr(current, "is_working", False) and getattr(proxy, "is_working", False):
            best[key] = proxy

    return list(best.values())
