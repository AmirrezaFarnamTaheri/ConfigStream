from __future__ import annotations

from typing import Callable, Iterable, List, Sequence

from .models import Proxy


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
            proxy for proxy in self._proxies if proxy.city and proxy.city.lower() in normalized
        ]
        return ProxyFilter(filtered)

    def by_protocol(self, protocols: Sequence[str]) -> "ProxyFilter":
        normalized = {protocol.lower() for protocol in protocols}
        filtered = [proxy for proxy in self._proxies if proxy.protocol.lower() in normalized]
        return ProxyFilter(filtered)

    def by_latency(self, *, min_ms: float = 0, max_ms: float | None = None) -> "ProxyFilter":
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
            proxy for proxy in self._proxies if proxy.asn and proxy.asn.upper() in normalized
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
        return ProxyFilter(sorted(self._proxies, key=lambda proxy: (proxy.country_code or "")))

    def chain(self, *filters: Callable[[Sequence[Proxy]], Iterable[Proxy]]) -> "ProxyFilter":
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
