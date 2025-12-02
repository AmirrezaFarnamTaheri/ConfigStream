import asyncio
import logging
import json
import time
from typing import Optional
from datetime import datetime, timezone

import aiohttp
from aiohttp_socks import ProxyConnector

from ..config import AppSettings
from ..models import Proxy
from ..converters import to_singbox_outbound
from ..security_validator import SecurityValidator
from .utils import SecureConfigContext

logger = logging.getLogger(__name__)

# Optional dependency
try:
    from singbox2proxy import SingBoxProxy as singbox_factory
except ImportError:
    singbox_factory = None
    logger.warning(
        "singbox2proxy not installed - Python fallback testing will be limited. "
        "Install with: pip install singbox2proxy"
    )


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

    def datetime_now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    async def test_direct(self, proxy: Proxy) -> Proxy:
        try:
            proto = "socks5" if "socks" in proxy.protocol else proxy.protocol
            url = f"{proto}://{proxy.address}:{proxy.port}"
            logger.debug(f"Testing direct connection: {url}")
            connector = ProxyConnector.from_url(url)
            async with aiohttp.ClientSession(connector=connector) as session:
                latency = await self._measure_latency_robust(session, proxy)
                if latency is not None:
                    proxy.latency = latency
                    proxy.is_working = True
                    if (
                        proxy.protocol in ["http", "socks", "socks5"]
                        and proxy.details.get("tls") != "tls"
                    ):
                        proxy.tags.append("insecure")
                    if self.strict_security:
                        await self._run_security_checks(session, proxy)
                else:
                    proxy.is_working = False
        except Exception as e:
            proxy.is_working = False
            proxy.details["error"] = str(e)

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

        outbound_config["tag"] = "proxy-test"
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
            "outbounds": [outbound_config],
        }
        config_content = json.dumps(full_config)

        with SecureConfigContext(config_content) as config_path:
            sb_instance = None
            try:
                if singbox_factory:
                    try:
                        start_time = time.monotonic()
                        sb_instance = await asyncio.wait_for(
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
                logger.warning(
                    f"Exception during proxy test for {proxy.address}:{proxy.port}: {e}"
                )
                proxy.is_working = False
                proxy.details["error"] = str(e)
            finally:
                if sb_instance:
                    try:
                        await asyncio.wait_for(
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
                        url, timeout=self.timeout, allow_redirects=False
                    ) as resp:
                        if 200 <= resp.status < 300:
                            latencies.append((time.monotonic() - start) * 1000)
                except Exception:
                    pass
            if not latencies:
                return None
            return sum(latencies) / len(latencies)

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
            if proxy is not None:
                proxy.tags.append("dirty_ip")
            return round(latency, 2)
        return None

    async def _run_security_checks(self, session: aiohttp.ClientSession, proxy: Proxy):
        if proxy.resolved_ip:
            # Lazy import to prevent circular dependency if any
            from ..security.blocklist import DEFAULT_BLOCKLIST

            if DEFAULT_BLOCKLIST.is_blocked(proxy.resolved_ip):
                proxy.is_working = False
                proxy.security_issues.setdefault("blocklist", []).append(
                    "FireHol Blocked (Late Check)"
                )
                return
        proxy.tags.append("secure-checked")
