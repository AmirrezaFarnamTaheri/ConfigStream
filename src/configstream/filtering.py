# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import random
import hashlib
import logging
from typing import Callable, Iterable, List, Sequence, Dict, Tuple, Any

from .models import Proxy, get_proxy_credential
from .config import AppSettings
from .utils.bool_parser import parse_tls_flag

logger = logging.getLogger(__name__)


def _is_better_proxy(candidate: Proxy, current: Proxy) -> bool:
    """Return True if candidate should replace current in dedup maps.

    Priority: working beats non-working, then lower latency wins.
    """
    if candidate.is_working and not current.is_working:
        return True
    if current.is_working and not candidate.is_working:
        return False
    # Same working status — prefer lower latency
    cur_lat = current.latency if current.latency is not None else float("inf")
    new_lat = candidate.latency if candidate.latency is not None else float("inf")
    return new_lat < cur_lat


def proxy_unique_key(
    p: Proxy,
) -> Tuple[str, str, int, str, str, str, str, str, str, str, str]:
    """
    Build a canonical stable identity for a proxy configuration.
    Used for "Soft Deduplication" (removing identical configs).
    Included fields: protocol, address, port, uuid, sni, path, serviceName (grpc),
    mode (grpc), host (ws/http), transport (vmess), security (tls/reality/etc)
    """
    proto = p.protocol.lower().strip()
    # Use address (hostname) for stable deduplication before testing
    # Normalize address by removing trailing dot (DNS root)
    addr = p.address.lower().strip().rstrip(".")
    port = int(p.port)
    uuid = (p.uuid or "").lower().strip()
    if not uuid:
        details = p.details or {}
        for key in (
            "uuid",
            "password",
            "auth",
            "private_key",
            "public_key",
            "peer_public_key",
            "psk",
            "key",
            "token",
        ):
            candidate = details.get(key)
            if isinstance(candidate, str) and candidate.strip():
                uuid = candidate.strip().lower()
                break

    # Transport details
    sni = (p.sni or "").lower().strip().rstrip(".")
    path = (p.path or "").strip()
    if path == "/":
        path = ""

    # Additional details for specificity
    details = p.details or {}
    service_name = str(details.get("serviceName", "")).strip()
    mode = str(details.get("mode", "")).strip()  # gRPC mode
    host = str(details.get("host", "")).lower().strip()  # WS host
    transport = str(details.get("net") or details.get("type") or "tcp").lower().strip()
    security = details.get("security")
    if security:
        security = str(security).lower().strip()
    else:
        security = "tls" if parse_tls_flag(details.get("tls")) else "none"

    return (
        proto,
        addr,
        port,
        uuid,
        sni,
        path,
        service_name,
        mode,
        host,
        transport,
        security,
    )


def dedupe_and_shuffle(proxies: List[Proxy]) -> List[Proxy]:
    """
    Deduplicate proxies keeping the highest quality version.
    Then shuffle them (deterministically if seed is set).
    """
    best: dict[Tuple[Any, ...], Proxy] = {}
    for proxy in proxies:
        key = proxy_unique_key(proxy)
        current = best.get(key)

        if current is None or _is_better_proxy(proxy, current):
            best[key] = proxy

    unique = list(best.values())

    seed_env = AppSettings().CONFIGSTREAM_SHUFFLE_SEED
    rng_seed: int | str | None = None
    if seed_env:
        try:
            rng_seed = int(seed_env)
        except ValueError:
            rng_seed = seed_env

    rng = random.Random(rng_seed)  # nosec B311
    rng.shuffle(unique)

    # Log deduplication statistics
    removed_count = len(proxies) - len(unique)
    if removed_count > 0:
        logger.info(
            f"Deduplication: {len(proxies)} -> {len(unique)} ({removed_count} duplicates removed)"
        )

    return unique


def filter_unique_endpoints(proxies: List[Proxy]) -> List[Proxy]:
    """
    Aggressive post-processing filter using Fuzzy Fingerprinting.
    Groups proxies by a hash of (Resolved IP, Port, UUID, Transport Path, SNI).
    This handles cases where the same server is listed with different remarks or slight URL variations.
    """
    # Key: Fingerprint Hash -> Proxy
    fingerprint_map: Dict[str, Proxy] = {}
    settings = AppSettings()
    include_protocol = not settings.DEDUP_IGNORE_PROTOCOL

    for p in proxies:
        # 1. Gather Core Identity Fields
        addr = (p.resolved_ip or p.address).lower().strip()
        port = str(p.port)
        cred = get_proxy_credential(p).lower().strip()

        # 2. Gather Transport Specifics (critical for differentiation)
        path = (p.path or "").strip()
        if path == "/":
            path = ""

        sni = (p.sni or "").lower().strip()

        # 3. Construct Fingerprint String
        # We ignore 'remarks' and 'title'. Protocol can be included if configured.
        # Format: [PROTOCOL|]IP:PORT|CREDENTIAL|PATH|SNI
        raw_fingerprint = f"{addr}:{port}|{cred}|{path}|{sni}"
        if include_protocol:
            raw_fingerprint = f"{p.protocol.lower().strip()}|{raw_fingerprint}"

        # 4. Hash it
        # Audit: SHA-256 for collision resistance
        fingerprint = hashlib.sha256(raw_fingerprint.encode("utf-8")).hexdigest()

        existing = fingerprint_map.get(fingerprint)
        if not existing:
            fingerprint_map[fingerprint] = p
        elif _is_better_proxy(p, existing):
            fingerprint_map[fingerprint] = p
        else:
            # Enrich existing with better metadata if candidate has it
            if (
                p.country_code
                and p.country_code != "XX"
                and existing.country_code == "XX"
            ):
                existing.country_code = p.country_code
                existing.country = p.country
                existing.city = p.city or existing.city
                existing.asn = p.asn or existing.asn
                existing.org = p.org or existing.org

    # Log endpoint filtering statistics
    removed_count = len(proxies) - len(fingerprint_map)
    if removed_count > 0:
        logger.info(
            f"Endpoint filtering: {len(proxies)} -> {len(fingerprint_map)} "
            f"({removed_count} duplicate endpoints removed)"
        )

    return list(fingerprint_map.values())


def _normalize_config_string(config: str) -> str:
    """Normalize a config string for deduplication purposes."""
    normalized = config.strip()
    if not normalized:
        return ""
    # Drop fragment remarks (common source of duplicate outputs)
    if "#" in normalized:
        normalized = normalized.split("#", 1)[0].strip()
    return normalized


def dedupe_by_config(proxies: List[Proxy]) -> List[Proxy]:
    """
    Final safety-net deduplication based on normalized config strings.
    This removes duplicates that differ only in tags/remarks.
    """
    best: dict[str, Proxy] = {}
    passthrough: List[Proxy] = []

    for proxy in proxies:
        if not proxy.config:
            passthrough.append(proxy)
            continue

        key = _normalize_config_string(proxy.config)
        if not key:
            passthrough.append(proxy)
            continue

        current = best.get(key)
        if current is None or _is_better_proxy(proxy, current):
            best[key] = proxy
            continue

    unique = list(best.values()) + passthrough
    removed_count = len(proxies) - len(unique)
    if removed_count > 0:
        logger.info(
            f"Config deduplication: {len(proxies)} -> {len(unique)} "
            f"({removed_count} duplicates removed)"
        )
    return unique


class ProxyFilter:
    """Utility for filtering and sorting collections of proxies."""

    def __init__(self, proxies: Sequence[Proxy]):
        self._proxies = list(proxies)

    def by_country(self, countries: Sequence[str]) -> "ProxyFilter":
        normalized = {country.upper() for country in countries}
        filtered = [
            proxy
            for proxy in self._proxies
            if proxy.country_code and proxy.country_code.upper() in normalized
        ]
        return ProxyFilter(filtered)

    def by_city(self, cities: Sequence[str]) -> "ProxyFilter":
        normalized = {city.lower() for city in cities}
        filtered = [
            proxy
            for proxy in self._proxies
            if proxy.city and proxy.city.lower() in normalized
        ]
        return ProxyFilter(filtered)

    def by_protocol(self, protocols: Sequence[str]) -> "ProxyFilter":
        normalized = {protocol.lower() for protocol in protocols}
        filtered = [
            proxy for proxy in self._proxies if proxy.protocol.lower() in normalized
        ]
        return ProxyFilter(filtered)

    def by_latency(
        self, *, min_ms: float = 0, max_ms: float | None = None
    ) -> "ProxyFilter":
        filtered: List[Proxy] = []
        for proxy in self._proxies:
            if proxy.latency is None:
                continue
            if proxy.latency < min_ms:
                continue
            if max_ms is not None and proxy.latency > max_ms:
                continue
            filtered.append(proxy)
        return ProxyFilter(filtered)

    def by_asn(self, asns: Sequence[str]) -> "ProxyFilter":
        normalized = {asn.upper() for asn in asns}
        filtered = [
            proxy
            for proxy in self._proxies
            if proxy.asn and proxy.asn.upper() in normalized
        ]
        return ProxyFilter(filtered)

    def sort_by_latency(self, *, ascending: bool = True) -> "ProxyFilter":
        return ProxyFilter(
            sorted(
                self._proxies,
                key=lambda proxy: proxy.latency or float("inf"),
                reverse=not ascending,
            )
        )

    def sort_by_country(self) -> "ProxyFilter":
        return ProxyFilter(
            sorted(self._proxies, key=lambda proxy: proxy.country_code or "")
        )

    def chain(
        self, *filters: Callable[[Sequence[Proxy]], Iterable[Proxy]]
    ) -> "ProxyFilter":
        result: List[Proxy] = self._proxies
        for filter_callable in filters:
            result = list(filter_callable(result))
        return ProxyFilter(result)

    def working_only(self) -> "ProxyFilter":
        """Filter to only working proxies."""
        return ProxyFilter([p for p in self._proxies if p.is_working])

    def limit(self, count: int) -> "ProxyFilter":
        """Limit to first N proxies."""
        return ProxyFilter(self._proxies[:count])

    def to_list(self) -> List[Proxy]:
        return list(self._proxies)
