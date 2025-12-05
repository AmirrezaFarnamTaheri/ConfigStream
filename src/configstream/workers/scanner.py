import asyncio
import json
import logging
import shutil
import os
from typing import List, Optional, Dict
from pathlib import Path

# Configure logger for this module
logger = logging.getLogger(__name__)


class WarpScannerWorker:
    """
    Orchestrates the 'configstream-tester' binary in 'scan' mode to
    actively discover fresh, low-latency Cloudflare WARP endpoints.
    """

    def __init__(self, binary_path: Optional[str] = None):
        """
        Initialize the worker by resolving the path to the Go binary.

        Resolution Order:
        1. Constructor argument (if provided)
        2. CONFIGSTREAM_TESTER_BIN environment variable
        3. PATH lookup (system-wide install)
        4. Common fallback locations (dev/deploy paths)
        """
        self.binary_path = self._resolve_binary(binary_path)
        self.available = self.binary_path is not None and os.path.exists(
            self.binary_path
        )

        if self.available:
            logger.debug(
                f"WarpScannerWorker initialized using binary: {self.binary_path}"
            )
        else:
            logger.warning(
                "WarpScannerWorker: Go binary not found. Active scanning will be disabled."
            )

    def _resolve_binary(self, explicit_path: Optional[str]) -> Optional[str]:
        """Helper to find the executable."""
        # 1. Check argument
        if explicit_path and os.path.exists(explicit_path):
            return explicit_path

        # 2. Check Environment Variable
        env_path = os.environ.get("CONFIGSTREAM_TESTER_BIN")
        if env_path and os.path.exists(env_path):
            return env_path

        # 3. Check PATH
        path_resolved = shutil.which("configstream-tester")
        if path_resolved:
            return path_resolved

        # 4. Fallback Checks
        common_locations = [
            Path.cwd() / "configstream-tester",
            Path.cwd() / "src/go/tester/configstream-tester",
            Path("/usr/local/bin/configstream-tester"),
            Path("/opt/configstream/bin/configstream-tester"),
        ]
        for loc in common_locations:
            if loc.exists():
                return str(loc)

        return None

    async def scan_endpoints(
        self, limit: int = 50, timeout: int = 5, max_latency: int = 800
    ) -> List[str]:
        """
        Executes the binary scan command and parses the output.

        Args:
            limit: Maximum number of IPs to find before stopping.
            timeout: UDP timeout per handshake attempt (seconds).
            max_latency: Latency threshold (ms). Results above this are discarded.

        Returns:
            List[str]: A list of valid IP addresses (e.g., ["162.159.192.1", ...])
        """
        if not self.available:
            logger.warning("Scan requested but binary is unavailable.")
            return []

        # Construct Command: ./configstream-tester -mode scan -limit 50 -timeout 5s
        cmd = [
            self.binary_path,
            "-mode",
            "scan",
            "-limit",
            str(limit),
            "-timeout",
            f"{timeout}s",
            "-workers",
            "100",  # High concurrency for scanning
        ]

        try:
            logger.info(
                f"Starting active WARP scan (Target: {limit} IPs, Timeout: {timeout}s)..."
            )

            # Create subprocess asynchronously
            # We pipe stdout to read JSON stream, stderr to capture logs
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            # Wait for the process to finish and capture output
            # Note: For massive scans, we might want to iterate stdout line-by-line
            # while running, but for <1000 items, communicate() is safe and simpler.
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"Scanner binary exited with error code {proc.returncode}")
                if stderr:
                    logger.error(f"Scanner stderr: {stderr.decode().strip()}")
                return []

            # Log any debug info from the binary (if present)
            if stderr and len(stderr) > 0:
                # Only log stderr at DEBUG level unless it's a crash
                logger.debug(f"Scanner internals: {stderr.decode().strip()}")

            # Parse Results
            clean_ips = []
            raw_output = stdout.decode()

            if not raw_output.strip():
                logger.warning("Scanner finished but produced no output.")
                return []

            for line in raw_output.splitlines():
                if not line.strip():
                    continue

                try:
                    # Expected JSON: {"ip":"1.2.3.4", "port":2408, "latency":45}
                    data = json.loads(line)

                    ip = data.get("ip")
                    latency = data.get("latency", 9999)

                    if ip and latency <= max_latency:
                        clean_ips.append(ip)

                except json.JSONDecodeError:
                    logger.debug(f"Skipping invalid JSON line from scanner: {line}")
                    continue

            logger.info(
                f"Active scan completed. Found {len(clean_ips)} valid IPs "
                f"(Request: {limit}, Max Latency: {max_latency}ms)."
            )
            return clean_ips

        except Exception as e:
            logger.error(
                f"Critical error during active scan execution: {e}", exc_info=True
            )
            return []
