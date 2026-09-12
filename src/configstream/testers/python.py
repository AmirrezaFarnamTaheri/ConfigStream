# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bounded Python fallback proxy tester.

The fallback never downloads or installs client binaries at runtime. Complex
protocols are tested only when sing-box and the optional wrapper are already
installed. The native Go tester remains the authoritative CI test path.
"""

from __future__ import annotations

import asyncio
import errno
import json
import logging
import shutil
import socket
import ssl
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from urllib.parse import quote

import aiohttp
from aiohttp_socks import ProxyConnector

from ..async_utils import safe_wait_for
from ..config import AppSettings
from ..converters import to_singbox_outbound
from ..intelligence.evasion import enrich_outbound_with_evasion
from ..models import Proxy
from ..security_validator import SecurityValidator
from ..utils.bool_parser import parse_tls_flag
from .utils import SecureConfigContext

logger = logging.getLogger(__name__)
_singbox_factory = None
_port_lease_lock = threading.Lock()
_leased_loopback_ports: set[int] = set()
_STARTUP_ATTEMPTS = 3


def _reserve_loopback_port() -> int:
    """Select an ephemeral loopback port for a sing-box HTTP inbound.

    singbox2proxy polls the explicit ``http_port`` passed to its constructor.
    Supplying a complete config with a port-zero mixed inbound therefore cannot
    become ready: sing-box listens on an OS-selected port while the wrapper
    polls a different one. The socket is closed immediately before sing-box
    starts, so a cross-process bind race remains possible and is handled by
    bounded startup retries below.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _lease_loopback_port() -> int:
    """Reserve a process-local port identity until wrapper startup completes."""
    with _port_lease_lock:
        for _ in range(32):
            port = _reserve_loopback_port()
            if port not in _leased_loopback_ports:
                _leased_loopback_ports.add(port)
                return port
    raise RuntimeError("could not lease a unique loopback port")


def _release_loopback_port(port: int) -> None:
    with _port_lease_lock:
        _leased_loopback_ports.discard(port)


def _is_bind_collision(exc: BaseException) -> bool:
    if isinstance(exc, OSError) and exc.errno in {errno.EADDRINUSE, 10048}:
        return True
    message = str(exc).lower()
    return "address already in use" in message or (
        "only one usage of each socket address" in message
    )


def _get_singbox_factory():
    """Return a wrapper only when a local sing-box executable is available.

    This prevents singbox2proxy from taking an implicit install/download path.
    Run 29336626898 reached that path and produced a command containing ``None``,
    which cascaded into 12,374 identical TypeError failures.
    """
    global _singbox_factory
    if _singbox_factory is not None:
        return _singbox_factory if _singbox_factory is not False else None
    binary = shutil.which("sing-box")
    if not binary:
        _singbox_factory = False
        logger.info("sing-box is not preinstalled; complex Python fallback is disabled")
        return None
    try:
        from singbox2proxy import SingBoxProxy  # type: ignore
    except ImportError:
        _singbox_factory = False
        logger.info(
            "singbox2proxy is not installed; complex Python fallback is disabled"
        )
        return None
    _singbox_factory = SingBoxProxy
    logger.debug("singbox2proxy enabled with preinstalled binary %s", binary)
    return _singbox_factory


def _stop_instance(instance: Any) -> None:
    try:
        instance.stop()
    except Exception as exc:
        logger.debug(
            "Failed to stop sing-box fallback: %s",
            SecurityValidator.sanitize_log_message(str(exc)),
        )


async def _start_instance(
    factory: Callable[..., Any],
    config: str,
    http_port: int,
    timeout: float,
    release_port: Optional[Callable[[], None]] = None,
) -> Any:
    """Keep worker-owned config/process resources alive across cancellation."""
    loop = asyncio.get_running_loop()

    ownership = threading.Lock()
    abandoned = False
    completed = None

    def construct() -> Any:
        nonlocal completed
        try:
            with SecureConfigContext(config) as config_path:
                instance = factory(config_path, http_port=http_port, socks_port=False)
        finally:
            if release_port is not None:
                release_port()
        with ownership:
            if not abandoned:
                completed = instance
                return instance
        # Cleanup stays in the worker even if the event loop is shutting down.
        _stop_instance(instance)
        return None

    def consume_late_result(future: asyncio.Future[Any]) -> None:
        try:
            future.result()
        except Exception as exc:
            logger.debug(
                "Abandoned sing-box startup failed: %s",
                SecurityValidator.sanitize_log_message(str(exc)),
            )

    try:
        pending = loop.run_in_executor(None, construct)
    except RuntimeError:
        if release_port is not None:
            release_port()
        raise
    try:
        return await safe_wait_for(asyncio.shield(pending), timeout=timeout)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        # Cancelling an executor future cannot stop its thread. Retain its
        # result so a process which finishes starting later is still stopped.
        with ownership:
            abandoned = True
            ready = completed
        if ready is not None:
            loop.run_in_executor(None, _stop_instance, ready)
        pending.add_done_callback(consume_late_result)
        raise


class PythonTester:
    def __init__(
        self,
        settings: AppSettings,
        timeout: float = 10.0,
        strict_security: bool = False,
    ):
        self.settings = settings
        self.timeout = timeout
        self.strict_security = strict_security
        self._warn_state: dict[str, tuple[float, int]] = {}
        self._warn_lock = asyncio.Lock()
        self._warn_window_sec = 60.0
        self._warn_burst = 5

    async def _should_log(self, key: str) -> bool:
        now = time.monotonic()
        async with self._warn_lock:
            window_start, count = self._warn_state.get(key, (now, 0))
            if now - window_start > self._warn_window_sec:
                window_start, count = now, 0
            self._warn_state[key] = (window_start, count + 1)
            return count < self._warn_burst

    @staticmethod
    def datetime_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    async def test_direct(self, proxy: Proxy) -> Proxy:
        proxy.details = dict(proxy.details or {})
        try:
            proto = (proxy.protocol or "").lower()
            if proto in {"socks", "socks5"}:
                proto = "socks5"
            elif proto == "socks4":
                proto = "socks4"
            elif proto == "https" or (
                proto == "http" and parse_tls_flag(proxy.details.get("tls"))
            ):
                proto = "https"
            user = (
                proxy.uuid
                or proxy.details.get("username")
                or proxy.details.get("user", "")
            )
            password = proxy.details.get("password") or ""
            auth = ""
            if user:
                auth = quote(str(user), safe="")
                if password:
                    auth += f":{quote(str(password), safe='')}"
                auth += "@"
            host = proxy.address
            if ":" in host and not host.startswith("["):
                host = f"[{host}]"
            connector_options = {}
            if proto == "https":
                # python-socks accepts HTTP CONNECT with a separate TLS context;
                # its URL parser rejects an https:// scheme.
                connector_options["proxy_ssl"] = await asyncio.to_thread(
                    ssl.create_default_context
                )
                proto = "http"
            connector = ProxyConnector.from_url(
                f"{proto}://{auth}{host}:{proxy.port}", **connector_options
            )
            async with aiohttp.ClientSession(connector=connector) as session:
                latency = await self._measure_latency_robust(session, proxy)
                proxy.is_working = latency is not None
                if latency is not None:
                    proxy.latency = latency
                    if proxy.protocol in {
                        "http",
                        "socks",
                        "socks5",
                        "socks4",
                    } and not parse_tls_flag(proxy.details.get("tls")):
                        proxy.tags.append("insecure")
                    if self.strict_security:
                        await self._run_security_checks(session, proxy)
        except Exception as exc:
            proxy.is_working = False
            proxy.details["tester_error_category"] = "direct_test_failed"
            proxy.details["error"] = SecurityValidator.sanitize_log_message(str(exc))
            logger.debug("Direct fallback failed: %s", proxy.details["error"])
        proxy.tested_at = self.datetime_now_iso()
        return proxy

    async def test_via_singbox(self, proxy: Proxy) -> Proxy:
        proxy.details = dict(proxy.details or {})
        if not proxy.config:
            proxy.is_working = False
            proxy.details["tester_error_category"] = "missing_config"
            proxy.details["failure_category"] = "tester_error"
            proxy.tested_at = self.datetime_now_iso()
            return proxy
        # The wrapper registers signal handlers at import and requires the
        # main thread. Process construction itself runs in the worker below.
        factory = _get_singbox_factory()
        if factory is None:
            proxy.is_working = False
            proxy.details["tester_error_category"] = "python_fallback_unavailable"
            proxy.details["failure_category"] = "tester_unavailable"
            proxy.tested_at = self.datetime_now_iso()
            return proxy
        outbound = to_singbox_outbound(proxy)
        if not outbound:
            proxy.is_working = False
            proxy.details["tester_error_category"] = "conversion_failed"
            proxy.details["failure_category"] = "tester_error"
            proxy.tested_at = self.datetime_now_iso()
            return proxy
        outbound = enrich_outbound_with_evasion(
            outbound,
            proxy.id,
            enable_utls=True,
            enable_alpn=True,
            enable_multiplexing=True,
        )
        extras = outbound.pop("_extra_outbounds", None)
        outbound["tag"] = "proxy-test"
        outbounds = [outbound]
        if isinstance(extras, list):
            outbounds.extend(item for item in extras if isinstance(item, dict))
        loop = asyncio.get_running_loop()
        instance = None
        try:
            for startup_attempt in range(_STARTUP_ATTEMPTS):
                http_port = _lease_loopback_port()
                config_content = json.dumps(
                    {
                        "log": {"level": "info"},
                        "inbounds": [
                            {
                                "type": "http",
                                "tag": "http-in",
                                "listen": "127.0.0.1",
                                "listen_port": http_port,
                            }
                        ],
                        "outbounds": outbounds,
                        "route": {"final": "proxy-test"},
                    }
                )
                try:
                    def release_http_port(port: int = http_port) -> None:
                        _release_loopback_port(port)

                    instance = await _start_instance(
                        factory,
                        config_content,
                        http_port,
                        self.timeout,
                        release_port=release_http_port,
                    )
                    break
                except asyncio.TimeoutError:
                    proxy.details["tester_error_category"] = "singbox_start_timeout"
                    proxy.details["failure_category"] = "tester_error"
                    if await self._should_log("singbox_start_timeout"):
                        logger.warning(
                            "sing-box fallback start timed out for %s",
                            SecurityValidator.sanitize_log_message(proxy.address),
                        )
                    proxy.is_working = False
                    return proxy
                except Exception as exc:
                    if (
                        _is_bind_collision(exc)
                        and startup_attempt + 1 < _STARTUP_ATTEMPTS
                    ):
                        logger.debug(
                            "sing-box fallback port collision; retrying startup"
                        )
                        continue
                    proxy.details["tester_error_category"] = "singbox_start_failed"
                    proxy.details["failure_category"] = "tester_error"
                    proxy.details["error"] = SecurityValidator.sanitize_log_message(
                        str(exc)
                    )
                    log_key = f"singbox_start_failed:{type(exc).__name__}"
                    if await self._should_log(log_key):
                        logger.warning(
                            "sing-box fallback start failed for %s: %s",
                            SecurityValidator.sanitize_log_message(
                                f"{proxy.address}:{proxy.port}"
                            ),
                            SecurityValidator.sanitize_log_message(
                                f"{type(exc).__name__}: {exc}"
                            ),
                        )
                    proxy.is_working = False
                    return proxy
            proxy_url = getattr(instance, "http_proxy_url", None)
            if not instance or not proxy_url:
                proxy.details["tester_error_category"] = "singbox_proxy_url_missing"
                proxy.details["failure_category"] = "tester_error"
                proxy.is_working = False
                return proxy
            async with aiohttp.ClientSession(
                connector=ProxyConnector.from_url(proxy_url)
            ) as session:
                latency = await self._measure_latency_robust(session, proxy)
                proxy.is_working = latency is not None
                if latency is not None:
                    proxy.latency = latency
                    if self.strict_security:
                        await self._run_security_checks(session, proxy)
        except Exception as exc:
            log_key = f"singbox_exception:{type(exc).__name__}"
            if await self._should_log(log_key):
                logger.warning(
                    "exception during bounded proxy fallback for %s: %s",
                    SecurityValidator.sanitize_log_message(
                        f"{proxy.address}:{proxy.port}"
                    ),
                    SecurityValidator.sanitize_log_message(str(exc)),
                )
            proxy.is_working = False
            proxy.details["tester_error_category"] = "singbox_runtime_failed"
            proxy.details["failure_category"] = "tester_error"
            proxy.details["error"] = SecurityValidator.sanitize_log_message(str(exc))
        finally:
            if instance:
                try:
                    await safe_wait_for(
                        loop.run_in_executor(None, _stop_instance, instance),
                        timeout=5.0,
                    )
                except asyncio.TimeoutError:
                    logger.debug("Sing-box fallback stop exceeded its deadline")
            proxy.tested_at = self.datetime_now_iso()
        return proxy

    async def _measure_latency_robust(
        self,
        session: aiohttp.ClientSession,
        proxy: Optional[Proxy] = None,
    ) -> Optional[float]:
        del proxy

        async def attempt(url: str) -> Optional[float]:
            values: list[float] = []
            for _ in range(2):
                try:
                    started = time.monotonic()
                    async with session.get(
                        url,
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                        allow_redirects=False,
                    ) as response:
                        if 200 <= response.status < 300:
                            values.append((time.monotonic() - started) * 1000)
                except Exception as exc:
                    logger.debug(
                        "Latency probe failed: %s",
                        SecurityValidator.sanitize_log_message(str(exc)),
                    )
            return round(sum(values) / len(values), 2) if values else None

        urls: list[str] = []
        if self.strict_security and self.settings.CANARY_URL:
            urls.append(self.settings.CANARY_URL)
        urls.extend(
            [
                self.settings.TEST_URLS.get(
                    "google", "https://www.google.com/generate_204"
                ),
                "http://cp.cloudflare.com/generate_204",
            ]
        )
        for url in urls:
            latency = await attempt(url)
            if latency is not None:
                return latency
        return None

    async def _run_security_checks(
        self, session: aiohttp.ClientSession, proxy: Proxy
    ) -> None:
        del session
        if proxy.resolved_ip:
            from ..security.blocklist import DEFAULT_BLOCKLIST

            if DEFAULT_BLOCKLIST.is_blocked(proxy.resolved_ip):
                proxy.security_issues.setdefault("blocklist", []).append(
                    "FireHol Blocked (Late Check)"
                )
                proxy.details["security_override"] = "blocklist"
        proxy.tags.append("secure-checked")
