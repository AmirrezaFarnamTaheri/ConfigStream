import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, ClassVar, Optional

import aiohttp
from aiohttp_socks import ProxyConnector

from .config import AppSettings
from .models import Proxy
from singbox2proxy import SingBoxProxy

if TYPE_CHECKING:
    from .test_cache import TestResultCache

logger = logging.getLogger(__name__)


class ProxyTester:
    """Abstract base class for proxy testers."""

    # Keep a class-level reference to the sing-box binary path to avoid repeated lookups
    _singbox_path: ClassVar[str | None] = None

    def __init__(
        self,
        timeout: float = 10.0,
        config: AppSettings | None = None,
        cache: Optional["TestResultCache"] = None,
    ) -> None:
        self.timeout = timeout
        self.config = config or AppSettings()
        self.cache = cache
        self.cache_hits = 0
        self.cache_misses = 0

    async def test(self, proxy: Proxy) -> Proxy:
        raise NotImplementedError


class SingBoxTester(ProxyTester):
    """Proxy tester using sing-box with optional caching."""

    async def test(self, proxy: Proxy) -> Proxy:
        """Tests a proxy using sing-box and aiohttp, with optional cache lookup."""
        # Check cache first if enabled
        if self.cache:
            cached_result = self.cache.get(proxy)
            if cached_result:
                self.cache_hits += 1
                logger.debug(
                    "Using cached result for %s:%s (working=%s, latency=%s)",
                    proxy.address,
                    proxy.port,
                    cached_result.is_working,
                    cached_result.latency,
                )
                return cached_result
            self.cache_misses += 1

        # Perform actual test
        sb_proxy: SingBoxProxy | None = None
        loop = asyncio.get_running_loop()
        try:
            # Run the synchronous SingBoxProxy constructor in a thread to avoid blocking the event loop.
            # The constructor itself calls start() and waits for the process to be ready.
            sb_proxy = await loop.run_in_executor(None, lambda: SingBoxProxy(proxy.config))

            if not sb_proxy or not sb_proxy.http_proxy_url:
                proxy.is_working = False
                proxy.security_issues.append("Proxy http_proxy_url is not set")
                return proxy

            connector = ProxyConnector.from_url(sb_proxy.http_proxy_url)

            # Optimize test URL order: try fastest URLs first
            # Google and Cloudflare typically respond fastest
            prioritized_urls = [
                self.config.TEST_URLS["google"],
                self.config.TEST_URLS["cloudflare"],
                self.config.TEST_URLS["gstatic"],
            ]
            fallback_urls = [
                url
                for name, url in self.config.TEST_URLS.items()
                if name not in {"google", "cloudflare", "gstatic"}
            ]
            test_urls = prioritized_urls + fallback_urls

            # Try multiple test URLs with optimized timeout
            for url_index, test_url in enumerate(test_urls):
                try:
                    # Use shorter timeout for subsequent URLs after first failure
                    current_timeout = self.timeout if url_index == 0 else min(self.timeout, 5.0)

                    async with aiohttp.ClientSession(connector=connector) as session:
                        # monotonic timer on current running loop
                        start_time = asyncio.get_running_loop().time()
                        async with session.get(
                            test_url,
                            timeout=aiohttp.ClientTimeout(total=current_timeout),
                        ) as response:
                            # Treat any 2xx as success; 204 is common, but many probes return 200.
                            if 200 <= response.status < 300:
                                end_time = asyncio.get_running_loop().time()
                                latency_ms = max((end_time - start_time) * 1000, 0.01)
                                proxy.latency = round(latency_ms, 2)
                                proxy.is_working = True
                                # Early exit on success - no need to test other URLs
                                break
                except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                    logger.debug(
                        f"Proxy {proxy.address}:{proxy.port} failed test URL {test_url} with {e.__class__.__name__}"
                    )
                    # try next URL
                    continue
                except Exception as e:
                    logger.debug(f"Test URL {test_url} failed with unexpected error: {e}")
                    continue

            if not proxy.is_working:
                proxy.security_issues.append("All test URLs failed")

        except RuntimeError as e:
            proxy.is_working = False
            proxy.security_issues.append(f"SingBox error: {e}")
            logger.debug(f"SingBoxProxy error for {proxy.config}: {e}")
        except Exception as e:
            proxy.is_working = False
            error_details = "[MASKED]" if self.config.MASK_SENSITIVE_DATA else str(e)
            proxy.security_issues.append(f"Connection failed: {error_details}")
            logger.error(f"Proxy test error for {proxy.config}: {str(e)[:100]}")
        finally:
            if sb_proxy:
                try:
                    # Run the synchronous stop() method in a thread.
                    await loop.run_in_executor(None, sb_proxy.stop)
                except Exception as e:
                    logger.debug(f"Error stopping SingBoxProxy: {e}")

        proxy.tested_at = datetime.now(timezone.utc).isoformat()

        # Store result in cache if enabled
        if self.cache:
            self.cache.set(proxy)

        return proxy

    def get_cache_stats(self) -> dict:
        """Get cache hit/miss statistics."""
        total = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total if total > 0 else 0.0
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total_tests": total,
            "hit_rate": round(hit_rate, 3),
        }
