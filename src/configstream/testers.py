import asyncio
import importlib
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Optional, cast

import aiohttp
from aiohttp_socks import ProxyConnector

from .config import AppSettings
from .models import Proxy
from .constants import TEST_URLS
from singbox2proxy import SingBoxProxy

if TYPE_CHECKING:
    from singbox2proxy import SingBoxProxy as _SingBoxProxy
    from .test_cache import TestResultCache

    SingBoxProxyType = _SingBoxProxy
else:
    SingBoxProxyType = Any  # pragma: no cover


SingBoxProxy: Callable[[str], Any] | None = None  # type: ignore[assignment,no-redef]  # noqa: F811

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
        max_retries: int = 2,
    ) -> None:
        self.timeout = timeout
        self.config = config or AppSettings()
        self.cache = cache
        self.cache_hits = 0
        self.cache_misses = 0
        self.max_retries = max_retries

    async def test(self, proxy: Proxy) -> Proxy:
        raise NotImplementedError


class SingBoxTester(ProxyTester):
    """Proxy tester using sing-box with optional caching and direct testing for HTTP/SOCKS5."""

    async def _test_direct_http_socks(self, proxy: Proxy) -> Optional[Proxy]:
        """
        Test HTTP/SOCKS5 proxies directly without Sing-Box for better performance.

        This bypasses the expensive process spawning overhead for simple proxy types.
        """
        try:
            # Determine proxy URL format
            if proxy.protocol.lower() in ("http", "https"):
                proxy_url = f"{proxy.protocol}://{proxy.address}:{proxy.port}"
            elif proxy.protocol.lower() in ("socks", "socks5", "socks4", "socks4a"):
                # Normalize to socks5
                protocol = (
                    "socks5"
                    if proxy.protocol.lower() in ("socks", "socks5")
                    else proxy.protocol.lower()
                )
                proxy_url = f"{protocol}://{proxy.address}:{proxy.port}"
            else:
                # Fallback to Sing-Box for complex protocols
                return None

            connector = ProxyConnector.from_url(proxy_url)
            prioritized_urls = [
                TEST_URLS["google"],
                TEST_URLS["cloudflare"],
                TEST_URLS["gstatic"],
            ]

            async with aiohttp.ClientSession(connector=connector) as session:
                for url_index, test_url in enumerate(prioritized_urls):
                    for retry in range(self.max_retries + 1):
                        try:
                            current_timeout = min(self.timeout, 5.0) if url_index > 0 else self.timeout

                            if retry > 0:
                                await asyncio.sleep(0.5 * (2 ** (retry - 1)))

                            timeout_config = aiohttp.ClientTimeout(
                                total=current_timeout,
                                connect=min(current_timeout * 0.3, 3.0),
                                sock_read=min(current_timeout * 0.5, 5.0),
                            )

                            start_time = asyncio.get_running_loop().time()
                            async with session.get(test_url, timeout=timeout_config) as response:
                                if 200 <= response.status < 300:
                                    end_time = asyncio.get_running_loop().time()
                                    latency_ms = max((end_time - start_time) * 1000, 0.01)
                                    proxy.latency = round(latency_ms, 2)
                                    proxy.is_working = True
                                    break

                            if proxy.is_working:
                                break
                        except (asyncio.TimeoutError, aiohttp.ClientError):
                            if retry == self.max_retries:
                                continue
                            continue

                    if proxy.is_working:
                        break

            if not proxy.is_working:
                if "connectivity" not in proxy.security_issues:
                    proxy.security_issues["connectivity"] = []
                proxy.security_issues["connectivity"].append("Direct test: all test URLs failed")

        except Exception as e:
            logger.debug(f"Direct test failed for {proxy.address}:{proxy.port}: {e}")
            return None

        proxy.tested_at = datetime.now(timezone.utc).isoformat()

        if self.cache:
            self.cache.set(proxy)

        return proxy

    async def test(self, proxy: Proxy) -> Proxy:
        """Tests a proxy using sing-box and aiohttp, with optional cache lookup and direct testing for HTTP/SOCKS5."""
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

        singbox_factory = self._get_singbox_factory()
        if proxy.protocol.lower() in ("http", "https", "socks", "socks5", "socks4", "socks4a"):
            logger.debug(
                f"Using direct test for {proxy.protocol} proxy {proxy.address}:{proxy.port}"
            )
            direct_result = await self._test_direct_http_socks(proxy)
            if direct_result:
                return direct_result
            logger.debug(
                f"Direct test failed, falling back to Sing-Box for {proxy.address}:{proxy.port}"
            )

        sb_proxy: Any = None
        loop = asyncio.get_running_loop()
        try:
            sb_proxy = await loop.run_in_executor(None, lambda: singbox_factory(proxy.config))

            if not sb_proxy or not sb_proxy.http_proxy_url:
                proxy.is_working = False
                if "configuration_error" not in proxy.security_issues:
                    proxy.security_issues["configuration_error"] = []
                proxy.security_issues["configuration_error"].append(
                    "Proxy http_proxy_url is not set"
                )
                return proxy

            connector = ProxyConnector.from_url(sb_proxy.http_proxy_url)
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

            async with aiohttp.ClientSession(connector=connector) as session:
                for url_index, test_url in enumerate(test_urls):
                    for retry in range(self.max_retries + 1):
                        try:
                            if url_index == 0:
                                current_timeout = self.timeout
                            elif url_index < 3:
                                current_timeout = min(self.timeout, 5.0)
                            else:
                                current_timeout = min(self.timeout, 3.0)

                            if retry > 0:
                                await asyncio.sleep(0.5 * (2 ** (retry - 1)))
                                logger.debug(
                                    f"Retry {retry}/{self.max_retries} for {proxy.address}:{proxy.port}"
                                )

                            timeout_config = aiohttp.ClientTimeout(
                                total=current_timeout,
                                connect=min(current_timeout * 0.3, 3.0),
                                sock_read=min(current_timeout * 0.5, 5.0),
                            )

                            start_time = asyncio.get_running_loop().time()
                            async with session.get(test_url, timeout=timeout_config) as response:
                                if 200 <= response.status < 300:
                                    end_time = asyncio.get_running_loop().time()
                                    latency_ms = max((end_time - start_time) * 1000, 0.01)
                                    proxy.latency = round(latency_ms, 2)
                                    proxy.is_working = True
                                    break

                            if proxy.is_working:
                                break
                        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                            if retry == self.max_retries:
                                logger.debug(
                                    f"Proxy {proxy.address}:{proxy.port} failed test URL "
                                    f"{test_url} after {retry + 1} attempts with {e.__class__.__name__}"
                                )
                            continue
                        except Exception as e:
                            if retry == self.max_retries:
                                logger.debug(
                                    f"Test URL {test_url} failed after {retry + 1} attempts "
                                    f"with unexpected error: {e}"
                                )
                            continue

                    if proxy.is_working:
                        break

            if not proxy.is_working:
                if "connectivity" not in proxy.security_issues:
                    proxy.security_issues["connectivity"] = []
                proxy.security_issues["connectivity"].append("All test URLs failed")

        except RuntimeError as e:
            proxy.is_working = False
            if "singbox_error" not in proxy.security_issues:
                proxy.security_issues["singbox_error"] = []
            proxy.security_issues["singbox_error"].append(f"SingBox error: {e}")
            logger.debug(f"SingBoxProxy error for {proxy.config}: {e}")
        except Exception as e:
            proxy.is_working = False
            error_details = "[MASKED]" if self.config.MASK_SENSITIVE_DATA else str(e)
            if "connectivity" not in proxy.security_issues:
                proxy.security_issues["connectivity"] = []
            proxy.security_issues["connectivity"].append(f"Connection failed: {error_details}")
            logger.error(f"Proxy test error for {proxy.config}: {str(e)[:100]}")
        finally:
            if sb_proxy:
                try:
                    await loop.run_in_executor(None, sb_proxy.stop)
                except Exception as e:
                    logger.debug(f"Error stopping SingBoxProxy: {e}")

        proxy.tested_at = datetime.now(timezone.utc).isoformat()

        if self.cache:
            self.cache.set(proxy)

        return proxy

    @staticmethod
    def _get_singbox_factory() -> Callable[[str], Any]:
        """Return a callable that constructs ``SingBoxProxy`` instances."""
        global SingBoxProxy
        if SingBoxProxy is not None:
            return cast(Callable[[str], Any], SingBoxProxy)
        try:
            module = importlib.import_module("singbox2proxy")
            SingBoxProxy = getattr(module, "SingBoxProxy")
        except Exception as exc:
            raise RuntimeError("singbox2proxy is not available") from exc
        return cast(Callable[[str], Any], SingBoxProxy)

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
