from collections import Counter
import asyncio
from urllib.parse import urlparse

from .dns_cache import DEFAULT_CACHE


async def prewarm_dns_cache(sources: list[str], top_n: int = 10):
    """
    Resolves the most common hostnames from a list of sources
    and populates the DNS cache.
    """
    host_counts = Counter(
        urlparse(source).hostname
        for source in sources
        if urlparse(source).hostname is not None
    )

    top_hosts = [
        host for host, _ in host_counts.most_common(top_n) if host is not None
    ]

    await asyncio.gather(
        *(DEFAULT_CACHE.resolve(host) for host in top_hosts),
        return_exceptions=True,  # Ignore failures
    )
