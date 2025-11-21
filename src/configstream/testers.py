"""
Secure Proxy Testing Module.
Handles the lifecycle of Sing-box instances and measures performance
with strict resource cleanup and security boundaries.
"""

import asyncio
import logging
import os
import stat
import tempfile
import atexit
import time
from typing import Optional, Set
from contextlib import contextmanager

import aiohttp
from aiohttp_socks import ProxyConnector
from bs4 import BeautifulSoup

try:
    from singbox2proxy import SingBoxProxy as singbox_factory
except ImportError:
    singbox_factory = None

from .config import AppSettings
from .models import Proxy
from .test_cache import TestResultCache
from .security.blocklist import DEFAULT_BLOCKLIST
from .security.honeypot import is_honeypot
from .security.utls_wrapper import test_tls_fingerprint
from .security.ss_ffi import verify_ss_rust

logger = logging.getLogger(__name__)

# Track temp files for failsafe cleanup at exit
_TEMP_FILES: Set[str] = set()

# Known SHA256 fingerprints for MITM detection (approximate list, in production this needs to be dynamic)
SUSPICIOUS_ISSUERS = [
    "mitmproxy",
    "Fiddler",
    "GoProxy",
    "Charles",
    "BurpSuite",
    "ConfigStream-Interceptor",
]


def _cleanup_temp_files():
    """Failsafe cleanup for any remaining config files."""
    for path in _TEMP_FILES:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except Exception:
            pass


atexit.register(_cleanup_temp_files)


@contextmanager
def SecureConfigContext(content: str):
    """
    Context manager that creates a secure temporary file for Sing-box config.
    Enforces 0600 permissions and guarantees deletion.
    """
    fd, path = tempfile.mkstemp(suffix=".json", text=True)
    _TEMP_FILES.add(path)
    try:
        # Secure: Only owner can read/write
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "w") as f:
            f.write(content)
        yield path
    finally:
        try:
            if os.path.exists(path):
                os.unlink(path)
            _TEMP_FILES.discard(path)
        except OSError as e:
            logger.warning("Failed to unlink temp file %s: %s", path, e)


class SingBoxTester:
    """
    Orchestrates the testing of proxies using Sing-box core.
    """

    def __init__(
        self,
        timeout: float = 10.0,
        cache: Optional[TestResultCache] = None,
        strict_security: bool = False,
        dry_run: bool = False,
    ):
        self.timeout = timeout
        self.cache = cache
        self.strict_security = strict_security
        self.settings = AppSettings()
        self.dry_run = dry_run

    async def test(self, proxy: Proxy) -> Proxy:
        """
        Main entry point for testing a proxy.
        """
        if self.dry_run:
            proxy.is_working = True
            proxy.latency = 123.45
            return proxy
        # 1. Check Cache
        if self.cache and (cached := self.cache.get(proxy)):
            return cached

        # 2. Direct Test for Standard Protocols (HTTP/SOCKS)
        # Optimization: Don't spin up Sing-box if we don't have to
        if proxy.protocol.lower() in ("http", "https", "socks", "socks5"):
            return await self._test_direct(proxy)

        # 3. Sing-box Test for Complex Protocols (Vmess, Vless, etc.)
        return await self._test_via_singbox(proxy)

    async def _test_direct(self, proxy: Proxy) -> Proxy:
        """Test HTTP/SOCKS proxies directly using aiohttp."""
        try:
            proto = "socks5" if "socks" in proxy.protocol else proxy.protocol
            url = f"{proto}://{proxy.address}:{proxy.port}"

            connector = ProxyConnector.from_url(url)
            async with aiohttp.ClientSession(connector=connector) as session:
                latency = await self._measure_latency_robust(session)

                if latency is not None:
                    proxy.latency = latency
                    proxy.is_working = True
                    if self.strict_security:
                        await self._run_security_checks(session, proxy)
                else:
                    proxy.is_working = False

        except Exception:
            proxy.is_working = False
            # Don't log every failure, it's noisy. Just mark as failed.

        self._finalize_result(proxy)
        return proxy

    async def _test_via_singbox(self, proxy: Proxy) -> Proxy:
        """Run test via Sing-box subprocess."""
        # Sanity Check: If config is empty, we can't test
        if not proxy.config:
            proxy.is_working = False
            return proxy

        loop = asyncio.get_running_loop()

        # Use secure context for the config file
        with SecureConfigContext(proxy.config) as config_path:
            sb_instance = None
            try:
                # Start Sing-box in a thread to avoid blocking the event loop
                # singbox_factory is synchronous
                # Security: Wrap in timeout to prevent hung subprocess from blocking event loop
                sb_instance = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: singbox_factory(config_path)),
                    timeout=self.timeout,
                )

                if not sb_instance or not sb_instance.http_proxy_url:
                    proxy.is_working = False
                    return proxy

                # Connect to the local SOCKS/HTTP proxy provided by Sing-box
                async with aiohttp.ClientSession(
                    connector=ProxyConnector.from_url(sb_instance.http_proxy_url)
                ) as session:
                    latency = await self._measure_latency_robust(session)

                    if latency is not None:
                        proxy.latency = latency
                        proxy.is_working = True
                        if self.strict_security:
                            await self._run_security_checks(session, proxy)
                    else:
                        proxy.is_working = False

            except Exception:
                proxy.is_working = False
                # logger.debug("Singbox test error: %s", e)
            finally:
                # Guarantee process cleanup
                if sb_instance:
                    try:
                        await asyncio.wait_for(
                            loop.run_in_executor(None, sb_instance.stop), timeout=5.0
                        )
                    except asyncio.TimeoutError:
                        logger.warning("Singbox stop timeout, process may be hung")
                    except Exception:
                        pass

        self._finalize_result(proxy)
        return proxy

    async def _measure_latency_robust(
        self, session: aiohttp.ClientSession
    ) -> Optional[float]:
        """
        Measure latency with Jitter Penalty.
        Returns None if connection fails.
        """
        latencies = []
        # We test against Google (generate_204) for speed
        target = self.settings.TEST_URLS.get(
            "google", "https://www.google.com/generate_204"
        )

        for _ in range(3):
            try:
                start = time.monotonic()
                async with session.get(
                    target, timeout=self.timeout, allow_redirects=False
                ) as resp:
                    if 200 <= resp.status < 300:
                        latencies.append((time.monotonic() - start) * 1000)
            except Exception:
                pass

        if not latencies:
            return None

        avg_latency = sum(latencies) / len(latencies)

        # Jitter Calculation
        if len(latencies) > 1:
            jitter = max(latencies) - min(latencies)
            # Penalize unstable connections
            if jitter > 100:
                avg_latency += jitter * 0.5

        return round(avg_latency, 2)

    async def _run_security_checks(self, session: aiohttp.ClientSession, proxy: Proxy):
        """
        Run integrity checks (Header Stripping, MITM, Injection, Reputation).
        """
        try:
            # Phase 4: Active Honeypot Detection (Port Scanning)
            if self.strict_security and proxy.resolved_ip:
                if await is_honeypot(proxy.resolved_ip):
                    proxy.security_issues.setdefault("integrity", []).append(
                        "HONEYPOT_DETECTED"
                    )
                    proxy.is_secure = False
                    return  # Fail fast

            # Phase 5: Shadowsocks Rust Verification (for SS proxies)
            if proxy.protocol == "shadowsocks":
                # Extract config details for checking
                if not verify_ss_rust(proxy.details):
                    proxy.security_issues.setdefault("crypto", []).append(
                        "SS_RUST_CHECK_FAILED"
                    )
                    proxy.is_working = False
                    return

            # Phase 4: TLS Fingerprint Randomization Test (Active)
            # If the proxy is connected, we verify if it supports randomized fingerprints.
            # We call the Go sidecar to perform a handshake with a randomized Client Hello.
            if self.strict_security and proxy.is_working:
                # We use the proxy address. If it's a local singbox port, we'd use that.
                # However, uTLS wrapper expects a proxy URL.
                # Since we are inside python, we might not have the local port easily if using direct.
                # If direct (HTTP/SOCKS), we use proxy.address:proxy.port
                # If Singbox, we are connected to a local port.

                # Simplification: We only test uTLS if we are in Direct mode or have easy access.
                # Given constraints, we log the check.
                try:
                    fp_result = await test_tls_fingerprint(
                        "https://www.google.com",
                        f"{proxy.address}:{proxy.port}",
                        "random",
                    )
                    if not fp_result:
                        # If uTLS fails but standard worked, it MIGHT be fingerprint blocking.
                        # We record it as a warning but don't strictly fail the proxy unless
                        # policy demands it, to avoid false positives from uTLS sidecar issues.
                        proxy.security_issues.setdefault("fingerprint", []).append(
                            "TLS_RANDOMIZATION_FAILED"
                        )
                        logger.debug(f"Proxy {proxy.address} failed randomized TLS handshake")
                except Exception as e:
                    logger.debug(f"uTLS check error: {e}")

            # 1. Blocklist/Reputation Check
            if self.strict_security:
                if proxy.resolved_ip and DEFAULT_BLOCKLIST.is_blocked(
                    proxy.resolved_ip
                ):
                    proxy.security_issues.setdefault("reputation", []).append(
                        "IP_IN_BLOCKLIST"
                    )
                    proxy.is_secure = False
                    return  # Fail fast

            # 2. Header Preservation Check
            headers = {"X-Canary": "ConfigStream-Check"}
            async with session.get(
                f"{self.settings.CANARY_URL}/headers", headers=headers, timeout=5
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("headers", {}).get("X-Canary") != "ConfigStream-Check":
                        proxy.security_issues.setdefault("headers", []).append(
                            "Header Stripping Detected"
                        )

            # 3. Active MITM Detection (Certificate Inspection)
            # We attempt to fetch the cert info from the underlying connection.
            # In aiohttp, accessing the transport's extra info 'ssl_object' gives the SSLSocket.
            # NOTE: This only works if the session verified SSL. If proxy terminates TLS, we see proxy's cert
            # IF it's a MITM proxy (CONNECT). If it's transparent, we see target's cert (or forged one).
            try:
                target_url = "https://www.google.com"
                async with session.get(target_url, timeout=5) as resp:
                    # Access the underlying transport to get SSL object
                    # This is hacky in aiohttp but necessary for deep inspection without a lower-level lib.
                    # However, aiohttp default SSLContext verifies chains. If we are here, the chain is trusted
                    # by the system trust store.

                    # To detect active MITM with a valid (but suspicious) cert:
                    # We check the Peer Certificate's Issuer.
                    if resp.connection and resp.connection.transport:
                        ssl_obj = resp.connection.transport.get_extra_info("ssl_object")
                        if ssl_obj:
                            cert = ssl_obj.getpeercert()
                            if cert:
                                issuer = dict(x[0] for x in cert["issuer"])
                                common_name = issuer.get("commonName", "")
                                organization = issuer.get("organizationName", "")

                                for suspicious in SUSPICIOUS_ISSUERS:
                                    if (
                                        suspicious.lower() in common_name.lower()
                                        or suspicious.lower() in organization.lower()
                                    ):
                                        proxy.security_issues.setdefault(
                                            "mitm", []
                                        ).append(f"Suspicious Issuer: {common_name}")
                                        proxy.is_secure = False
            except Exception:
                # Connection failed or couldn't get cert - implicit failure handled elsewhere
                pass

            # 4. Honey Pot / Injection Detection
            # Visit a known static page and check if unexpected elements are injected (ads, redirects)
            try:
                # Use a lightweight target that shouldn't change often, e.g. example.com
                target_url = "http://example.com"
                async with session.get(target_url, timeout=5) as resp:
                    content = await resp.text()
                    soup = BeautifulSoup(content, "html.parser")

                    # Check for unexpected scripts or iframes
                    if (
                        len(soup.find_all("script")) > 0
                        or len(soup.find_all("iframe")) > 0
                    ):
                        # Example.com has 0 scripts and 0 iframes usually.
                        # If we see them, it's likely ad injection.
                        proxy.security_issues.setdefault("integrity", []).append(
                            "HTML_INJECTION_DETECTED"
                        )
                        proxy.is_secure = False

                    # Check title
                    if (
                        not soup.title
                        or not soup.title.string
                        or "Example Domain" not in soup.title.string
                    ):
                        proxy.security_issues.setdefault("integrity", []).append(
                            "WRONG_CONTENT_RETURNED"
                        )
                        proxy.is_secure = False

            except Exception:
                # Timeout or other error during honeypot check
                pass

        except Exception:
            # Don't fail the whole proxy if security check times out
            pass

    def _finalize_result(self, proxy: Proxy):
        """Update proxy metadata and cache."""
        proxy.tested_at = datetime_now_iso()
        if self.cache:
            self.cache.set(proxy)


def datetime_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
