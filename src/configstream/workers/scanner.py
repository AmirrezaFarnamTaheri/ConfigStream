# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import json
import logging
import shutil
import os
from typing import List, Optional, Dict, Any
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
            # Check if disabled by CI policy before warning about missing binary
            is_ci = os.environ.get("CI") == "true"

            from configstream.config import AppSettings

            force_scanner = AppSettings().FORCE_SCANNER

            if is_ci and not force_scanner:
                logger.info("WarpScannerWorker: Scanner disabled by CI policy.")
            else:
                logger.warning(
                    "WarpScannerWorker: Go binary not found. Active scanning will be disabled."
                )

    def _resolve_binary(self, explicit_path: Optional[str]) -> Optional[str]:
        """Helper to find the executable."""

        # 0. CI Environment Check
        # Disable by default in CI to prevent:
        #   - UDP firewall blocks (GitHub Actions blocks outbound UDP)
        #   - Rate limiting from Cloudflare (shared IP pool is flagged)
        #   - Pipeline hangs on network timeouts

        # To enable in CI, set FORCE_SCANNER=true (use with caution)
        is_ci = os.environ.get("CI") == "true"

        from configstream.config import AppSettings

        settings = AppSettings()

        force_scanner = settings.FORCE_SCANNER

        if is_ci and not force_scanner:
            logger.info(
                "Scanner disabled: Running in CI environment. "
                "Set FORCE_SCANNER=true to override (not recommended). "
                "Falling back to static IP lists."
            )
            return None
        elif is_ci and force_scanner:
            logger.warning(
                "Scanner FORCE ENABLED in CI. This may cause pipeline failures "
                "due to UDP firewall blocks or rate limiting."
            )

        # 1. Check argument
        if explicit_path and os.path.exists(explicit_path):
            return explicit_path

        # 2. Check Environment Variable
        env_path = settings.CONFIGSTREAM_TESTER_BIN
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
        from configstream.config import AppSettings

        settings = AppSettings()
        if not settings.ALLOW_ACTIVE_SCANNING and not settings.FORCE_SCANNER:
            logger.info(
                "Warp scan skipped: active scanning is disabled (ALLOW_ACTIVE_SCANNING=false)."
            )
            return []

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
            # Ensure cmd only contains strings
            str_cmd = [str(c) for c in cmd if c is not None]
            proc = await asyncio.create_subprocess_exec(
                *str_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            # Wait for the process to finish and capture output
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
                logger.warning(
                    "Scanner finished with exit code 0 but produced NO output. (Possible Firewall/Network Block)"
                )
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

    async def scan_dns_hijack(self, ips: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Executes the binary in 'dns-scan' mode to check for DNS hijacking.

        Args:
            ips: List of IPs to check. If None, uses binary defaults.

        Returns:
            List[Dict]: List of result objects (ip, is_hijacked, reason, etc.)
        """
        if not self.available:
            logger.warning("DNS scan requested but binary is unavailable.")
            return []

        cmd = [
            self.binary_path,
            "-mode",
            "dns-scan",
            "-workers",
            "20",
        ]

        try:
            logger.info("Starting DNS hijack scan...")

            # Ensure cmd only contains strings
            str_cmd = [str(c) for c in cmd if c is not None]

            proc = await asyncio.create_subprocess_exec(
                *str_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdin_data = None
            if ips:
                # Join with newlines
                stdin_data = ("\n".join(ips) + "\n").encode("utf-8")

            stdout, stderr = await proc.communicate(input=stdin_data)

            if proc.returncode != 0:
                logger.error(f"DNS Scanner exited with error code {proc.returncode}")
                if stderr:
                    logger.error(f"DNS Scanner stderr: {stderr.decode().strip()}")
                return []

            results = []
            raw_output = stdout.decode()

            for line in raw_output.splitlines():
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    results.append(data)
                except json.JSONDecodeError:
                    continue

            logger.info(f"DNS scan completed. Checked {len(results)} servers.")
            return results

        except Exception as e:
            logger.error(f"Critical error during DNS scan: {e}", exc_info=True)
            return []
