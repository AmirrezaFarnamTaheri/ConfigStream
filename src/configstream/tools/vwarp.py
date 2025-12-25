import asyncio
import shutil
import logging
import json
from pathlib import Path
from typing import Any, Dict, List, cast, Tuple, Optional

logger = logging.getLogger(__name__)


class VwarpTool:
    """
    Controller for the voidr3aper-anon/Vwarp binary.
    Handles scanning, config generation, and transport tunneling.
    """

    def __init__(self):
        self.binary = shutil.which("vwarp")
        if not self.binary:
            # Fallback for local testing if not in PATH
            self.binary = "/usr/local/bin/vwarp"
        self._tunnel_proc: Optional[asyncio.subprocess.Process] = None

    async def is_available(self) -> bool:
        """Quick health check."""
        if shutil.which("vwarp"):
            return True
        if Path(self.binary).exists():
            return True
        return False

    async def scan_endpoints(self, rtt_limit: str = "800ms") -> List[Tuple[str, int]]:
        """
        Runs 'vwarp --scan' to harvest unblocked Cloudflare IPs.
        Returns a list of (host, port) tuples.
        """
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

    async def start_tunnel(self, bind_addr: str = "127.0.0.1", port: int = 10808) -> bool:
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
            self._tunnel_proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            # Give it a moment to initialize
            await asyncio.sleep(1)

            if self._tunnel_proc.returncode is not None:
                logger.error(f"Vwarp tunnel exited immediately with code {self._tunnel_proc.returncode}")
                self._tunnel_proc = None
                return False

            return True
        except Exception as e:
            logger.warning(f"Failed to start Vwarp tunnel: {e}")
            return False

    async def stop_tunnel(self):
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
