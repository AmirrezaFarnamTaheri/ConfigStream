# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import ipaddress
import logging
import socket
from secrets import choice as secure_choice
from urllib.parse import urlparse, urljoin
from typing import Any, Dict, Optional, Tuple, List, Union
import httpx

from configstream.concurrency_manager import ConcurrencyManager
from configstream.config import AppSettings
from configstream.circuit_breaker import CircuitBreakerManager
from configstream.dns_cache import prewarm_dns_cache
from configstream.adaptive_timeout import AdaptiveTimeout
from configstream.http_client import get_client
from configstream.source_quality import SourceQualityTracker
from configstream.security_validator import SecurityValidator
from configstream.fetcher_worker import FetchResult

from .interfaces import IFetcher

logger = logging.getLogger(__name__)

# Use AppSettings if available, otherwise default
try:
    MAX_RESPONSE_SIZE = AppSettings().MAX_RESPONSE_SIZE
except Exception:
    logging.getLogger(__name__).debug("Suppressed broad exception", exc_info=True)
    MAX_RESPONSE_SIZE = 10 * 1024 * 1024

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
]

FETCH_INTERNAL_HOST_SUFFIXES = (".local", ".localhost", ".lan", ".internal")


def _reject_source_url(url: str, block_private_networks: bool = True) -> Optional[str]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return "Invalid URL"
    if not parsed.hostname:
        return "Invalid URL host"
    if parsed.username or parsed.password:
        return "Source URL credentials are not allowed"

    host = parsed.hostname.strip("[]").rstrip(".").lower()
    if len(host) > 253:
        return "Source URL host is too long"
    if host == "localhost" or host.endswith(FETCH_INTERNAL_HOST_SUFFIXES):
        return "Source URL targets an internal hostname"

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        if not all(part for part in host.split(".")):
            return "Source URL host is invalid"
        return None

    if block_private_networks and not ip.is_global:
        return "Source URL targets a private or non-global address"
    return None


def _resolve_redirect_url(
    current_url: str,
    location: Optional[str],
    block_private_networks: bool = True,
) -> Tuple[Optional[str], Optional[str]]:
    if not location:
        return None, "Redirect response missing Location header"
    candidate = urljoin(current_url, location.strip())
    reason = _reject_source_url(
        candidate, block_private_networks=block_private_networks
    )
    if reason:
        return None, f"Unsafe redirect target: {reason}"
    return candidate, None


async def _reject_source_dns(
    url: str,
    block_private_networks: bool = True,
    validate_dns: bool = True,
) -> Tuple[Optional[str], Optional[str]]:
    """Validate DNS resolution of *url* and return (error, validated_ip).

    SECURITY FIX (#493): Returns the validated IP so callers can pin the
    connection, preventing DNS-rebinding TOCTOU attacks.
    """
    if not validate_dns or not block_private_networks:
        return None, None

    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        return "Invalid URL host", None

    host = host.strip("[]")
    try:
        ip = ipaddress.ip_address(host)
        # Already an IP literal — no DNS needed
        return None, str(ip)
    except ValueError:
        pass

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(
            host,
            port,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror:
        return "Source URL host could not be resolved", None
    except OSError:
        return "Source URL host DNS validation failed", None

    resolved_ips = {
        sockaddr[0].strip("[]")
        for *_prefix, sockaddr in infos
        if sockaddr and sockaddr[0]
    }
    if not resolved_ips:
        return "Source URL host resolved to no addresses", None

    for raw_ip in resolved_ips:
        try:
            ip = ipaddress.ip_address(raw_ip)
        except ValueError:
            return "Source URL host resolved to an invalid address", None
        if not ip.is_global:
            return "Source URL host resolves to a private or non-global address", None

    # Return the first validated IP for connection pinning
    validated_ip = next(iter(resolved_ips))
    return None, validated_ip


async def fetch_from_source(
    client: httpx.AsyncClient,
    source: str,
    app_settings: Any = None,
    max_retries: int = 3,
    rate_limiter: Any = None,
    breaker_manager: Any = None,
    timeout_tracker: Any = None,
    retry_delay: float = 1.0,
    timeout: float | None = None,
    **kwargs: Any,  # Accept extra kwargs to satisfy Mypy/callers
) -> Any:
    """
    Robust fetcher implementation handling retries, circuit breaking, rate limiting,
    and response size limits.
    """

    if app_settings is None:
        app_settings = AppSettings()

    loop = asyncio.get_running_loop()
    safe_source = SecurityValidator.sanitize_log_message(source)

    # Validate URL
    url_error = _reject_source_url(
        source,
        block_private_networks=bool(app_settings.FETCH_BLOCK_PRIVATE_NETWORKS),
    )
    if not source or url_error:
        return FetchResult(
            success=False,
            source=source,
            content="",
            error=url_error or "Invalid URL",
            status_code=0,
        )

    # Sanitize malformed raw.githubusercontent URLs
    if "raw.githubusercontent" in source and "github.com" not in source:
        parsed = urlparse(source)
        if parsed.netloc.endswith(".raw.githubusercontent.com"):
            return FetchResult(
                success=False,
                source=source,
                content="",
                error="Malformed GitHub URL",
                status_code=0,
            )

    # Circuit Breaker Check
    breaker = None
    if breaker_manager:
        try:
            parsed = urlparse(source)
            host = parsed.netloc
            key = host
        except Exception:
            logging.getLogger(__name__).debug("Suppressed broad exception", exc_info=True)
            key = source

        breaker = await breaker_manager.get_breaker(key)

        is_open = breaker.is_open()
        if asyncio.iscoroutine(is_open):
            is_open = await is_open

        if is_open:
            should_log_open = False
            should_log_fn = getattr(breaker, "should_log_open", None)
            if callable(should_log_fn):
                maybe_should_log = should_log_fn()
                if asyncio.iscoroutine(maybe_should_log):
                    should_log_open = await maybe_should_log
                else:
                    should_log_open = bool(maybe_should_log)
            if should_log_open:
                logger.warning(
                    "Circuit breaker opened for host %s; skipping fetches temporarily.",
                    SecurityValidator.sanitize_log_message(str(key)),
                )
            return FetchResult(
                success=False,
                source=source,
                content="",
                error="Circuit Breaker Open",
                status_code=0,
            )

    # Rate Limiter Pre-check: retry until a token is available.
    # Ensures the limiter enforces the per-source cap even under concurrent load.
    if rate_limiter:
        while not await rate_limiter.is_allowed(source):
            wait_time = await rate_limiter.get_wait_time(source)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            else:
                # Avoid busy-spinning if get_wait_time returns 0.
                await asyncio.sleep(0.01)

    headers = {"User-Agent": secure_choice(USER_AGENTS)}
    attempt = 0
    last_error = None

    # Use instance limit if passed, else global default
    max_size_raw = app_settings.MAX_RESPONSE_SIZE if app_settings else MAX_RESPONSE_SIZE
    try:
        max_size = int(max_size_raw)
    except (TypeError, ValueError):
        max_size = 0
    try:
        max_redirects = max(0, int(app_settings.FETCH_MAX_REDIRECTS))
    except (TypeError, ValueError):
        max_redirects = 5
    validate_dns = bool(getattr(app_settings, "FETCH_VALIDATE_DNS", True))

    current_url = source
    redirects_followed = 0
    while attempt < max_retries:
        start_ts = loop.time()
        try:
            dns_error, validated_ip = await _reject_source_dns(
                current_url,
                block_private_networks=bool(app_settings.FETCH_BLOCK_PRIVATE_NETWORKS),
                validate_dns=validate_dns,
            )
            if dns_error:
                response_time = loop.time() - start_ts
                if timeout_tracker:
                    await timeout_tracker.record_attempt(
                        source, response_time, success=False
                    )
                if breaker:
                    await breaker.record_failure()
                return FetchResult(
                    success=False,
                    source=source,
                    content="",
                    error=dns_error,
                    status_code=0,
                    response_time=response_time,
                )

            # SECURITY FIX (#493): Pin the validated IP to prevent DNS-rebinding
            # TOCTOU attacks. Replace hostname with validated IP in URL and set
            # Host header so the TLS SNI remains correct.
            pinned_url = current_url
            host_header = None
            if validated_ip:
                parsed = urlparse(current_url)
                original_host = parsed.hostname
                if original_host and original_host != validated_ip:
                    # Build URL with IP literal, preserving port and path
                    netloc = validated_ip
                    if parsed.port:
                        netloc = f"{validated_ip}:{parsed.port}"
                    pinned_url = parsed._replace(netloc=netloc).geturl()
                    host_header = original_host

            # Jitter / Timeout Tracking
            effective_timeout = float(timeout) if timeout is not None else 30.0
            if timeout_tracker:
                adaptive_timeout = timeout_tracker.get_timeout(source)
                if timeout is not None:
                    adaptive_timeout = min(adaptive_timeout, float(timeout))
                effective_timeout = adaptive_timeout
                jitter = await timeout_tracker.get_jitter(source)
                if jitter > 2.0:
                    logger.info(f"High Jitter detected for {safe_source}: {jitter}s")

            request_headers = dict(headers)
            if host_header:
                request_headers["Host"] = host_header

            async with client.stream(
                "GET",
                pinned_url,
                headers=request_headers,
                timeout=effective_timeout,
                follow_redirects=False,
            ) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    if redirects_followed >= max_redirects:
                        response_time = loop.time() - start_ts
                        if timeout_tracker:
                            await timeout_tracker.record_attempt(
                                source, response_time, success=False
                            )
                        if breaker:
                            await breaker.record_failure()
                        return FetchResult(
                            success=False,
                            source=source,
                            content="",
                            error="Too many redirects",
                            status_code=response.status_code,
                            response_time=response_time,
                        )
                    next_url, redirect_error = _resolve_redirect_url(
                        current_url,
                        response.headers.get("Location"),
                        block_private_networks=bool(
                            app_settings.FETCH_BLOCK_PRIVATE_NETWORKS
                        ),
                    )
                    if redirect_error or next_url is None:
                        response_time = loop.time() - start_ts
                        if timeout_tracker:
                            await timeout_tracker.record_attempt(
                                source, response_time, success=False
                            )
                        if breaker:
                            await breaker.record_failure()
                        return FetchResult(
                            success=False,
                            source=source,
                            content="",
                            error=redirect_error or "Unsafe redirect target",
                            status_code=response.status_code,
                            response_time=response_time,
                        )
                    current_url = next_url
                    redirects_followed += 1
                    continue

                # Check Status
                if response.status_code == 429:
                    response_time = loop.time() - start_ts
                    if timeout_tracker:
                        await timeout_tracker.record_attempt(
                            source, response_time, success=False
                        )
                    if breaker:
                        await breaker.record_failure()
                    retry_after = response.headers.get("Retry-After")
                    # Retry-After may be delta-seconds or an HTTP-date; only
                    # honor numeric values and clamp to a sane ceiling so a
                    # hostile/buggy server cannot stall the pipeline.
                    wait = 2.0
                    if retry_after:
                        try:
                            wait = min(max(float(retry_after), 0.0), 30.0)
                        except (TypeError, ValueError):
                            wait = 2.0
                    await asyncio.sleep(wait)
                    attempt += 1
                    last_error = "Rate limited"
                    continue

                if response.status_code in [404, 410]:
                    response_time = loop.time() - start_ts
                    if timeout_tracker:
                        await timeout_tracker.record_attempt(
                            source, response_time, success=False
                        )
                    if breaker:
                        await breaker.record_failure()
                    return FetchResult(
                        success=False,
                        source=source,
                        content="",
                        error=f"Permanent Error: {response.status_code}",
                        status_code=response.status_code,
                        response_time=response_time,
                    )

                if response.status_code >= 500:
                    response_time = loop.time() - start_ts
                    if timeout_tracker:
                        await timeout_tracker.record_attempt(
                            source, response_time, success=False
                        )
                    if breaker:
                        await breaker.record_failure()
                    attempt += 1
                    last_error = f"HTTP {response.status_code}"
                    await asyncio.sleep(retry_delay * (2**attempt))
                    continue

                if response.status_code >= 400:
                    response_time = loop.time() - start_ts
                    if timeout_tracker:
                        await timeout_tracker.record_attempt(
                            source, response_time, success=False
                        )
                    if breaker:
                        await breaker.record_failure()
                    return FetchResult(
                        success=False,
                        source=source,
                        content="",
                        error=f"HTTP {response.status_code}",
                        status_code=response.status_code,
                        response_time=response_time,
                    )

                # Content Length Check
                content_len = response.headers.get("Content-Length")
                content_len_int = None
                if content_len:
                    try:
                        content_len_int = int(content_len)
                    except (TypeError, ValueError):
                        content_len_int = None
                if max_size > 0 and content_len_int and content_len_int > max_size:
                    response_time = loop.time() - start_ts
                    if timeout_tracker:
                        await timeout_tracker.record_attempt(
                            source, response_time, success=False
                        )
                    if breaker:
                        await breaker.record_failure()
                    return FetchResult(
                        success=False,
                        source=source,
                        content="",
                        error="Response too large",
                        status_code=response.status_code,
                        response_time=response_time,
                    )

                # Stream Content
                content_parts = []
                current_size = 0
                async for chunk in response.aiter_bytes():
                    current_size += len(chunk)
                    if max_size > 0 and current_size > max_size:
                        response_time = loop.time() - start_ts
                        if timeout_tracker:
                            await timeout_tracker.record_attempt(
                                source, response_time, success=False
                            )
                        if breaker:
                            await breaker.record_failure()
                        return FetchResult(
                            success=False,
                            source=source,
                            content="",
                            error="Response too large",
                            status_code=response.status_code,
                            response_time=response_time,
                        )
                    content_parts.append(chunk)

                content = b"".join(content_parts)

                # Decode
                text_content = content.decode("utf-8", errors="ignore")

                # Handle empty 200 OK responses gracefully
                if response.status_code == 200 and (
                    not text_content or not text_content.strip()
                ):
                    logger.info(
                        f"Source {safe_source} returned 200 OK but empty content."
                    )
                    response_time = loop.time() - start_ts
                    if timeout_tracker:
                        await timeout_tracker.record_attempt(
                            source, response_time, success=True
                        )
                    if breaker:
                        await breaker.record_success()
                    return FetchResult(
                        success=True,  # Valid HTTP transaction
                        source=source,
                        content="",  # Empty
                        status_code=200,
                        error="Empty content",  # Informative, not exception
                        response_time=response_time,
                    )

                response_time = loop.time() - start_ts
                if timeout_tracker:
                    await timeout_tracker.record_attempt(
                        source, response_time, success=True
                    )
                if breaker:
                    await breaker.record_success()
                return FetchResult(
                    success=True,
                    source=source,
                    content=text_content,
                    status_code=response.status_code,
                    error=None,
                    response_time=response_time,
                )

        except asyncio.CancelledError:
            logger.warning(f"Fetch for {safe_source} cancelled by outer signal.")
            # Propagate cancellation to abort fetch immediately
            raise
        except Exception as e:
            last_error = str(e)
            if timeout_tracker:
                try:
                    await timeout_tracker.record_attempt(
                        source, loop.time() - start_ts, success=False
                    )
                except Exception as tracker_exc:
                    logger.debug(
                        "Timeout tracker failure for %s: %s",
                        safe_source,
                        SecurityValidator.sanitize_log_message(str(tracker_exc)),
                    )
            if breaker:
                try:
                    await breaker.record_failure()
                except Exception as breaker_exc:
                    logger.debug(
                        "Circuit breaker failure accounting failed for %s: %s",
                        safe_source,
                        SecurityValidator.sanitize_log_message(str(breaker_exc)),
                    )
            attempt += 1
            await asyncio.sleep(retry_delay)

    return FetchResult(
        success=False,
        source=source,
        content="",
        error=f"Max retries exceeded: {last_error}",
        status_code=0,
    )


class _SimpleRateLimiter:
    """Minimal per-source token-bucket rate limiter.

    Replaces the ``rate_limiter = None`` dead-code assignment in
    ``fetch_multiple_sources`` (P1-7 fix).  Each source URL gets its own
    token bucket that replenishes at ``rate_per_second`` tokens per second
    and bursts up to ``burst`` tokens.
    """

    def __init__(self, rate_per_second: float = 2.0, burst: int = 5):
        self._rate = rate_per_second
        self._burst = burst
        # Map source -> (tokens, last_refill_time) tuple
        self._buckets: Dict[str, Tuple[float, float]] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(self, source: str) -> bool:
        async with self._lock:
            now = asyncio.get_event_loop().time()
            tokens, last = self._buckets.get(source, (float(self._burst), now))
            elapsed = now - last
            tokens = min(self._burst, tokens + elapsed * self._rate)
            if tokens >= 1.0:
                self._buckets[source] = (tokens - 1.0, now)
                return True
            self._buckets[source] = (tokens, now)
            return False

    async def get_wait_time(self, source: str) -> float:
        async with self._lock:
            now = asyncio.get_event_loop().time()
            tokens, _ = self._buckets.get(source, (float(self._burst), now))
            if tokens >= 1.0:
                return 0.0
            return (1.0 - tokens) / self._rate


async def fetch_multiple_sources(
    sources: List[str],
    max_concurrent: int = 10,
    timeout: int = 30,
    per_host_limit: int = 4,
    client: Optional[httpx.AsyncClient] = None,
    use_adaptive_timeout: bool = True,
    quality_tracker: Optional[SourceQualityTracker] = None,
    breaker_manager: Optional[CircuitBreakerManager] = None,
) -> Dict[str, FetchResult]:
    """High-level entry point for batch fetching.

    Orchestrates rate limits, DNS pre-warming, and concurrency.
    """
    results: Dict[str, FetchResult] = {}
    app_settings = AppSettings()

    # Initialize Components
    timeout_tracker = AdaptiveTimeout() if use_adaptive_timeout else None
    # Wire a real per-source rate limiter (was dead ``rate_limiter = None``,
    # P1-7 fix).  Uses a simple token-bucket so that no single source can be
    # hammered on retries even if the circuit breaker has not opened yet.
    rate_limiter: Optional[_SimpleRateLimiter] = _SimpleRateLimiter(
        rate_per_second=app_settings.FETCH_RATE_LIMIT_RPS
        if hasattr(app_settings, "FETCH_RATE_LIMIT_RPS")
        else 2.0
    )
    if breaker_manager is None:
        breaker_manager = CircuitBreakerManager(
            failure_threshold=app_settings.CIRCUIT_TRIP_CONN_ERRORS,
            recovery_timeout=app_settings.CIRCUIT_OPEN_SEC,
        )

    # Setup Concurrency Control
    loop = asyncio.get_running_loop()
    controller = ConcurrencyManager(loop, initial_limit=per_host_limit)
    await controller.start_tuner()
    global_sem = asyncio.Semaphore(max_concurrent)

    # Optimization: Pre-warm DNS (Best effort for HTTP sources)
    logger.info(f"Pre-warming DNS for {len(sources)} sources...")
    loop = asyncio.get_running_loop()
    dns_start = loop.time()
    await prewarm_dns_cache(sources)
    dns_dur = float(loop.time() - dns_start)
    logger.info(f"DNS pre-warming completed in {dns_dur:.2f}s.")

    async def _worker(
        http_client: httpx.AsyncClient, source: str
    ) -> Tuple[str, FetchResult]:
        async with global_sem:
            # Use keyword arguments for clarity
            res = await fetch_from_source(
                http_client,
                source,
                app_settings=app_settings,
                rate_limiter=rate_limiter,
                controller=controller,
                breaker_manager=breaker_manager,
                timeout_tracker=timeout_tracker,
                quality_tracker=quality_tracker,
                timeout=timeout,
            )
            return source, res

    try:
        logger.info(
            f"Starting parallel fetch for {len(sources)} sources (max_concurrent={max_concurrent})"
        )
        start_time = asyncio.get_running_loop().time()
        if client:
            tasks = [_worker(client, s) for s in sources]
            try:
                completed = await asyncio.gather(*tasks)
                for src, res in completed:
                    results[src] = res
            except Exception as e:
                logger.error(f"Error during fetch gather: {e}")
                # Note: If client was passed in, caller is responsible for cleanup
                raise
        else:
            async with get_client() as new_client:
                tasks = [_worker(new_client, s) for s in sources]
                completed = await asyncio.gather(*tasks)
                for src, res in completed:
                    results[src] = res

        duration = asyncio.get_running_loop().time() - start_time
        logger.info(f"Batch fetch completed in {duration:.2f}s")
    finally:
        await controller.stop_tuner()
        if timeout_tracker:
            timeout_tracker.save()

    success_count = sum(1 for r in results.values() if r.success)
    total_bytes = sum(
        len(r.content) for r in results.values() if r.success and r.content
    )
    logger.info(
        f"Fetch Summary: {success_count}/{len(sources)} sources successful. "
        f"Total data fetched: {total_bytes / 1024:.2f} KB"
    )

    return results


class HttpFetcher(IFetcher):
    """IFetcher adapter over the module-level fetch_from_source pipeline."""

    def __init__(
        self, client=None, settings=None, breaker_manager=None, timeout_tracker=None
    ):
        self.client = client
        self.settings = settings
        self.breaker_manager = breaker_manager
        self.timeout_tracker = timeout_tracker

    async def fetch(self, source: str) -> FetchResult:
        return await fetch_from_source(
            self.client,
            source,
            app_settings=self.settings,
            breaker_manager=self.breaker_manager,
            timeout_tracker=self.timeout_tracker,
        )
