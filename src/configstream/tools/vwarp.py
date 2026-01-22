# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import shutil
import logging
import json
import time
import os
from pathlib import Path
from typing import Any, Dict, List, cast, Tuple, Optional

from ..constants import VWARP_SOCKS5_PORT, VWARP_BIND_ADDRESS

logger = logging.getLogger(__name__)


class VwarpTool:
    """
    Controller for the voidr3aper-anon/Vwarp binary.
    Handles scanning, config generation, and transport tunneling.
    """

    def __init__(self) -> None:
        binary = shutil.which("vwarp")
        if not binary:
            # Fallback for local testing if not in PATH
            # Check specific fallback paths or env var
            possible_paths = ["/usr/local/bin/vwarp", "/opt/vwarp/vwarp", "./vwarp"]
            for p in possible_paths:
                if Path(p).exists():
                    binary = p
                    break
            else:
                binary = (
                    "vwarp"  # Default to name if not found, to fail gracefully later
                )

        self.binary: str = binary
        self._tunnel_proc: Optional[asyncio.subprocess.Process] = None

    async def is_available(self) -> bool:
        """Quick health check."""
        # CI Check: Disable unless forced
        is_ci = os.environ.get("CI") == "true"

        # Lazy import to avoid circular dependency
        from configstream.config import AppSettings

        force_scanner = AppSettings().FORCE_SCANNER

        if is_ci and not force_scanner:
            logger.debug("Vwarp disabled in CI environment (FORCE_SCANNER not set).")
            return False

        if shutil.which("vwarp"):
            return True
        if self.binary and Path(self.binary).exists():
            return True
        return False

    async def scan_endpoints(self, rtt_limit: str = "800ms") -> List[Tuple[str, int]]:
        """
        Runs 'vwarp --scan' to harvest unblocked Cloudflare IPs.
        Returns a list of (host, port) tuples.
        """
        from configstream.config import AppSettings

        settings = AppSettings()
        if not settings.ALLOW_ACTIVE_SCANNING and not settings.FORCE_SCANNER:
            logger.info(
                "Vwarp scan skipped: active scanning is disabled (ALLOW_ACTIVE_SCANNING=false)."
            )
            return []

        if not await self.is_available():
            logger.debug("❌ Vwarp binary missing. Cannot scan.")
            return []

        # Command: vwarp --scan --rtt 800ms --verbose
        cmd = [self.binary, "--scan", "--rtt", rtt_limit]

        try:
            logger.info("📡 Starting Vwarp active scanner...")
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            # Give it 30 seconds max to find IPs
            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                return []

            # Parse Output
            endpoints: List[Tuple[str, int]] = []
            if stdout:
                output_text = stdout.decode(errors="ignore")
                for line in output_text.splitlines():
                    # Expected format: "162.159.192.10:2408 - 150ms"
                    if ":" in line and "ms" in line:
                        clean_ep = line.split()[0].strip()
                        host = clean_ep
                        port = 2408  # Default

                        if ":" in clean_ep:
                            # If vwarp output includes port, parse it
                            # Format often is IP:PORT or [IPv6]:PORT
                            # The logic below already handles port parsing if it's in the string
                            # So we double check if existing logic covers it.
                            # Existing logic attempts to split by last colon.
                            # So this is likely already covered, but let's make it robust.
                            # Handle IPv6 addresses in brackets [ipv6]:port
                            if clean_ep.startswith("["):
                                # IPv6 format: [2001:db8::1]:2408
                                bracket_end = clean_ep.find("]")
                                if bracket_end > 0:
                                    host = clean_ep[1:bracket_end]
                                    rest = clean_ep[bracket_end + 1 :]
                                    if rest.startswith(":"):
                                        try:
                                            port = int(rest[1:])
                                        except ValueError:
                                            pass
                                else:
                                    host = clean_ep
                            else:
                                # IPv4 format: 162.159.192.10:2408
                                parts = clean_ep.rsplit(":", 1)
                                if len(parts) == 2:
                                    host = parts[0]
                                    try:
                                        port = int(parts[1])
                                    except ValueError:
                                        pass
                                else:
                                    host = clean_ep

                        endpoints.append((host, port))

            logger.info(f"✅ Vwarp found {len(endpoints)} healthy endpoints.")
            return endpoints

        except Exception as e:
            logger.error(f"Vwarp scan failed: {e}")
            return []

    async def generate_masque_config(self, preset: str = "gfw") -> Dict[str, Any]:
        """
        Exports a MASQUE-enabled Sing-box configuration.
        """
        if not await self.is_available():
            return {}

        cmd = [self.binary, "--export-singbox", "--masque-preset", preset]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            result = json.loads(stdout.decode(errors="ignore"))
            return cast(Dict[str, Any], result)
        except Exception:
            return {}

    async def _wait_for_port(self, host: str, port: int, timeout: int = 45) -> bool:
        """Polls the given host:port until it accepts connections."""
        probe_host = host
        if host in ("0.0.0.0", "::", ""):
            probe_host = "127.0.0.1"

        start = time.time()
        while time.time() - start < timeout:
            try:
                # Use asyncio to avoid blocking the event loop
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(probe_host, port), timeout=1
                )
                writer.close()
                await writer.wait_closed()
                return True
            except (OSError, asyncio.TimeoutError, ConnectionRefusedError):
                # Throttling: wait a bit longer or use exponential backoff to reduce CPU/Net load
                await asyncio.sleep(1.0)
        return False

    async def start_tunnel(
        self, bind_addr: str = VWARP_BIND_ADDRESS, port: int = VWARP_SOCKS5_PORT
    ) -> bool:
        """
        Starts the Vwarp SOCKS5 tunnel in the background.
        """
        if not await self.is_available():
            return False

        if self._tunnel_proc:
            # Already running
            return True

        cmd = [self.binary, "--bind", f"{bind_addr}:{port}"]
        try:
            logger.info(f"🚀 Starting Vwarp SOCKS5 Tunnel on {bind_addr}:{port}...")
            # Capture stdout/stderr for debugging if it fails
            self._tunnel_proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Robust port checking
            is_ready = await self._wait_for_port(bind_addr, port)
            if not is_ready:
                logger.error("Vwarp Tunnel started but port check timed out.")

                # Check for immediate exit and logs
                if self._tunnel_proc.returncode is not None:
                    stdout, stderr = await self._tunnel_proc.communicate()
                    if stdout:
                        logger.debug(f"Vwarp stdout: {stdout.decode(errors='ignore')}")
                    if stderr:
                        logger.error(f"Vwarp stderr: {stderr.decode(errors='ignore')}")
                else:
                    # Kill and read logs
                    try:
                        self._tunnel_proc.terminate()
                        # Allow brief time for logs to flush
                        try:
                            stdout, stderr = await asyncio.wait_for(
                                self._tunnel_proc.communicate(), timeout=1.0
                            )
                            if stderr:
                                logger.error(
                                    f"Vwarp stderr before kill: {stderr.decode(errors='ignore')}"
                                )
                        except asyncio.TimeoutError:
                            self._tunnel_proc.kill()
                    except Exception as e:
                        logger.debug(f"Error killing hung vwarp: {e}")

                self._tunnel_proc = None
                return False

            # Check if it died immediately after port check success (rare but possible)
            if self._tunnel_proc.returncode is not None:
                logger.error(
                    f"Vwarp tunnel exited immediately with code {self._tunnel_proc.returncode}"
                )
                self._tunnel_proc = None
                return False

            # Start background task to consume logs so buffer doesn't fill up
            # We don't really need the logs unless it crashes, but we must consume pipe
            async def consume_stream(stream, level):
                while stream and not stream.at_eof():
                    line = await stream.readline()
                    if line:
                        logger.log(
                            level, f"Vwarp: {line.decode(errors='ignore').strip()}"
                        )

            asyncio.create_task(consume_stream(self._tunnel_proc.stdout, logging.DEBUG))
            asyncio.create_task(
                consume_stream(self._tunnel_proc.stderr, logging.WARNING)
            )

            return True
        except Exception as e:
            logger.warning(f"Failed to start Vwarp tunnel: {e}")
            if self._tunnel_proc:
                try:
                    self._tunnel_proc.kill()
                except ProcessLookupError:
                    pass
                self._tunnel_proc = None
            return False

    async def stop_tunnel(self) -> None:
        """
        Stops the background tunnel process.
        """
        if self._tunnel_proc:
            logger.info("Stopping Vwarp tunnel...")
            try:
                self._tunnel_proc.terminate()
                try:
                    await asyncio.wait_for(self._tunnel_proc.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    self._tunnel_proc.kill()
            except ProcessLookupError:
                pass
            except Exception as e:
                logger.warning(f"Error stopping Vwarp tunnel: {e}")
            finally:
                self._tunnel_proc = None
