import asyncio
import shutil
import logging
import json
from pathlib import Path
from typing import List

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

    async def is_available(self) -> bool:
        """Quick health check."""
        return bool(shutil.which("vwarp") or Path(self.binary).exists())

    async def scan_endpoints(self, rtt_limit: str = "800ms") -> List[str]:
        """
        Runs 'vwarp --scan' to harvest unblocked Cloudflare IPs.
        Returns a list of 'IP:PORT' strings.
        """
        if not await self.is_available():
            # Only log error if we expected it to be there, otherwise it might just be local env
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
            endpoints = []
            if stdout:
                output_text = stdout.decode(errors="ignore")
                for line in output_text.splitlines():
                    # Regex or string splitting to find IP:PORT
                    # Expected format: "162.159.192.10:2408 - 150ms"
                    if ":" in line and "ms" in line:
                        clean_ep = line.split()[0].strip()
                        endpoints.append(clean_ep)

            logger.info(f"✅ Vwarp found {len(endpoints)} healthy endpoints.")
            return endpoints

        except Exception as e:
            logger.error(f"Vwarp scan failed: {e}")
            return []

    async def generate_masque_config(self, preset: str = "gfw") -> dict:
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
            return json.loads(stdout.decode(errors="ignore"))
        except Exception:
            return {}
