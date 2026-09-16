# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import json
import logging
import shutil
import os
from typing import List, Optional
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
        from configstream.security_validator import SecurityValidator
        from configstream.testers.go_tester.binary_security import (
            initialize_binary_identity,
            minimal_subprocess_environment,
            verify_binary_identity,
        )

        settings = AppSettings()
        if not settings.ALLOW_ACTIVE_SCANNING and not settings.FORCE_SCANNER:
            logger.info(
                "Warp scan skipped: active scanning is disabled (ALLOW_ACTIVE_SCANNING=false)."
            )
            return []

        if not self.available or not self.binary_path:
            logger.warning("Scan requested but binary is unavailable.")
            return []

        try:
            identity = await asyncio.to_thread(
                initialize_binary_identity, self.binary_path
            )
        except (OSError, ValueError) as exc:
            logger.error("Scanner binary rejected: %s", type(exc).__name__)
            self.available = False
            return []
        if not await asyncio.to_thread(verify_binary_identity, identity):
            logger.error("Scanner binary failed integrity verification")
            self.available = False
            return []
        self.binary_path = str(identity.path)

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

            # Create subprocess asynchronously with a minimal environment so
            # unrelated pipeline credentials are never inherited by the tester.
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=minimal_subprocess_environment(settings),
            )

            # Wait for the process to finish and capture output, bounded by an
            # overall deadline so a hung/zombie scanner binary cannot block the
            # pipeline indefinitely. The per-handshake timeout is enforced by the
            # binary; this is a defensive outer bound derived from it.
            scan_deadline = min(300, max(30, timeout * 4 + 30))
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=scan_deadline
                )
            except asyncio.TimeoutError:
                logger.error(
                    "WARP scan exceeded overall deadline of %ss; killing scanner.",
                    scan_deadline,
                )
                try:
                    proc.kill()
                    await proc.wait()
                except ProcessLookupError:
                    pass
                return []

            safe_stderr = SecurityValidator.sanitize_log_message(
                stderr.decode(errors="replace").strip()
            )
            if proc.returncode != 0:
                logger.error(f"Scanner binary exited with error code {proc.returncode}")
                if safe_stderr:
                    logger.error("Scanner stderr: %s", safe_stderr[:1000])
                return []

            # Log any debug info from the binary (if present), sanitized and bounded.
            if safe_stderr:
                logger.debug("Scanner internals: %s", safe_stderr[:1000])

            # Parse Results
            clean_ips = []
            raw_output = stdout.decode(errors="replace")

            if not raw_output.strip():
                # In CI or restricted environments, exit code 0 with no output might happen
                # But we should have caught CI above. If it happens here, it's likely a network block.
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
                    if not isinstance(data, dict):
                        continue

                    ip = data.get("ip")
                    latency = data.get("latency", 9999)
                    try:
                        latency_value = float(latency)
                    except (TypeError, ValueError):
                        continue

                    if isinstance(ip, str) and ip and latency_value <= max_latency:
                        clean_ips.append(ip)

                except json.JSONDecodeError:
                    logger.debug("Skipping invalid JSON line from scanner")
                    continue

            logger.info(
                f"Active scan completed. Found {len(clean_ips)} valid IPs "
                f"(Request: {limit}, Max Latency: {max_latency}ms)."
            )
            return clean_ips

        except (OSError, ValueError, RuntimeError) as exc:
            logger.error(
                "Critical error during active scan execution: %s",
                type(exc).__name__,
                exc_info=True,
            )
            return []
