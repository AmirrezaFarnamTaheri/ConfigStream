# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
import json
import time
import os
from typing import Optional
from datetime import datetime, timezone

import aiohttp
from aiohttp_socks import ProxyConnector
from urllib.parse import quote

from ..config import AppSettings
from ..models import Proxy
from ..converters import to_singbox_outbound
from ..security_validator import SecurityValidator
from ..utils.bool_parser import parse_tls_flag
from ..async_utils import safe_wait_for
from .utils import SecureConfigContext

logger = logging.getLogger(__name__)

_singbox_factory = None


def _get_singbox_factory():
    """Lazy import to avoid import-time side effects in tests."""
    global _singbox_factory
    if _singbox_factory is not None:
        return _singbox_factory
    try:
        from singbox2proxy import SingBoxProxy as singbox_factory  # type: ignore

        _singbox_factory = singbox_factory
    except ImportError:
        _singbox_factory = False
        logger.info(
            "singbox2proxy not installed - Python fallback testing for complex protocols (VLESS/VMess) unavailable. "
            "Direct protocols (SOCKS/HTTP) will still be tested."
        )
    return _singbox_factory if _singbox_factory is not False else None


class PythonTester:
    def __init__(
        self,
        settings: AppSettings,
        timeout: float = 10.0,
        strict_security: bool = False,
    ):
        # Fix for Sing-box 1.11+ deprecation warning/fatal error
        os.environ["ENABLE_DEPRECATED_WIREGUARD_OUTBOUND"] = "true"
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
                window_start = now
                count = 0
            if count < self._warn_burst:
                self._warn_state[key] = (window_start, count + 1)
                return True
            self._warn_state[key] = (window_start, count + 1)
            return False

    def datetime_now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    async def test_direct(self, proxy: Proxy) -> Proxy:
        try:
            proto = proxy.protocol.lower()
            if proto in ("socks", "socks5"):
                proto = "socks5"
            elif proto == "socks4":
                proto = "socks4"
            elif proto == "https":
                proto = "https"
            elif proto == "http" and parse_tls_flag(proxy.details.get("tls")):
                proto = "https"

            user = (
                proxy.uuid
                or proxy.details.get("username")
                or proxy.details.get("user", "")
            )
            password = proxy.details.get("password") or ""
            auth = ""
            if user:
                auth = f"{quote(str(user))}"
                if password:
                    auth += f":{quote(str(password))}"
                auth += "@"

            host = proxy.address
            if ":" in host and not host.startswith("["):
                host = f"[{host}]"

            url = f"{proto}://{auth}{host}:{proxy.port}"
            logger.debug(
                "Testing direct connection: %s",
                SecurityValidator.sanitize_log_message(url),
            )
            connector = ProxyConnector.from_url(url)
            async with aiohttp.ClientSession(connector=connector) as session:
                latency = await self._measure_latency_robust(session, proxy)
                if latency is not None:
                    proxy.latency = latency
                    proxy.is_working = True
                    if proxy.protocol in [
                        "http",
                        "socks",
                        "socks5",
                        "socks4",
                    ] and not parse_tls_flag(proxy.details.get("tls")):
                        proxy.tags.append("insecure")
                    if self.strict_security:
                        await self._run_security_checks(session, proxy)
                else:
                    proxy.is_working = False
        except Exception as e:
            proxy.is_working = False
            proxy.details["error"] = SecurityValidator.sanitize_log_message(str(e))

        proxy.tested_at = self.datetime_now_iso()
        return proxy

    async def test_via_singbox(self, proxy: Proxy) -> Proxy:
        if not proxy.config:
            proxy.is_working = False
            return proxy

        loop = asyncio.get_running_loop()
        outbound_config = to_singbox_outbound(proxy)
        if not outbound_config:
            proxy.is_working = False
            return proxy

        extra_outbounds = outbound_config.pop("_extra_outbounds", None)
        outbound_config["tag"] = "proxy-test"
        outbounds = [outbound_config]
        if isinstance(extra_outbounds, list):
            for extra in extra_outbounds:
                if isinstance(extra, dict):
                    outbounds.append(extra)
        full_config = {
            "log": {"level": "info"},
            "inbounds": [
                {
                    "type": "mixed",
                    "tag": "mixed-in",
                    "listen": "127.0.0.1",
                    "listen_port": 0,
                }
            ],
            "outbounds": outbounds,
        }
        config_content = json.dumps(full_config)

        with SecureConfigContext(config_content) as config_path:
            sb_instance = None
            try:
                singbox_factory = _get_singbox_factory()
                if singbox_factory:
                    try:
                        start_time = time.monotonic()
                        sb_instance = await safe_wait_for(
                            loop.run_in_executor(
                                None, lambda: singbox_factory(config_path)
                            ),
                            timeout=self.timeout,
                        )
                        logger.debug(
                            f"Sing-box instance started in {time.monotonic() - start_time:.4f}s"
                        )
                    except asyncio.TimeoutError:
                        safe_addr = SecurityValidator.sanitize_log_message(
                            getattr(proxy, "address", "unknown")
                        )
                        if await self._should_log("singbox_start_timeout"):
                            logger.warning(
                                f"Sing-box instance start timed out for proxy {safe_addr}"
                            )
                        proxy.is_working = False
                        return proxy

                    if not sb_instance or not sb_instance.http_proxy_url:
                        proxy.is_working = False
                        return proxy

                    async with aiohttp.ClientSession(
                        connector=ProxyConnector.from_url(sb_instance.http_proxy_url)
                    ) as session:
                        latency = await self._measure_latency_robust(session, proxy)
                        if latency is not None:
                            proxy.latency = latency
                            proxy.is_working = True
                            if self.strict_security:
                                await self._run_security_checks(session, proxy)
                        else:
                            proxy.is_working = False
                else:
                    logger.warning(
                        "Skipping test: 'singbox2proxy' library not found. Install it or use the Go tester."
                    )
                    proxy.is_working = False
            except Exception as e:
                if await self._should_log("singbox_exception"):
                    logger.warning(
                        "Exception during proxy test for %s: %s",
                        SecurityValidator.sanitize_log_message(
                            f"{proxy.address}:{proxy.port}"
                        ),
                        SecurityValidator.sanitize_log_message(str(e)),
                    )
                proxy.is_working = False
                proxy.details["error"] = SecurityValidator.sanitize_log_message(str(e))
            finally:
                if sb_instance:
                    try:
                        await safe_wait_for(
                            loop.run_in_executor(None, sb_instance.stop), timeout=5.0
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to stop Sing-box instance gracefully: {e}"
                        )

        proxy.tested_at = self.datetime_now_iso()
        return proxy

    async def _measure_latency_robust(
        self, session: aiohttp.ClientSession, proxy: Optional[Proxy] = None
    ) -> Optional[float]:
        async def _try_url(url: str) -> Optional[float]:
            latencies = []
            for _ in range(2):
                try:
                    start = time.monotonic()
                    async with session.get(
                        url,
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                        allow_redirects=False,
                    ) as resp:
                        if 200 <= resp.status < 300:
                            latencies.append((time.monotonic() - start) * 1000)
                except Exception:
                    pass
            if not latencies:
                return None
            return sum(latencies) / len(latencies)

        if self.strict_security and self.settings.CANARY_URL:
            latency = await _try_url(self.settings.CANARY_URL)
            if latency is not None:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        f"Latency check passed via CANARY_URL: {latency:.2f}ms"
                    )
                return round(latency, 2)

        google_url = self.settings.TEST_URLS.get(
            "google", "https://www.google.com/generate_204"
        )
        latency = await _try_url(google_url)
        if latency is not None:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Latency check passed via Google: {latency:.2f}ms")
            return round(latency, 2)

        fallback_url = "http://cp.cloudflare.com/generate_204"
        latency = await _try_url(fallback_url)
        if latency is not None:
            # Removed "dirty_ip" tag to prevent unfair washing/filtering of valid proxies
            # from regions that block Google but allow Cloudflare.
            return round(latency, 2)
        return None

    async def _run_security_checks(self, session: aiohttp.ClientSession, proxy: Proxy):
        if proxy.resolved_ip:
            # Lazy import to prevent circular dependency if any
            from ..security.blocklist import DEFAULT_BLOCKLIST

            if DEFAULT_BLOCKLIST.is_blocked(proxy.resolved_ip):
                proxy.security_issues.setdefault("blocklist", []).append(
                    "FireHol Blocked (Late Check)"
                )
                proxy.details["security_override"] = "blocklist"
        proxy.tags.append("secure-checked")
