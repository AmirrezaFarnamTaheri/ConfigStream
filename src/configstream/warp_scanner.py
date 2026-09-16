# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import json
import logging
import os
import shutil
from pathlib import Path
from typing import List, Optional

from configstream.config import AppSettings
from configstream.security_validator import SecurityValidator
from configstream.testers.go_tester.binary_security import (
    BinaryIdentity,
    initialize_binary_identity,
    minimal_subprocess_environment,
    verify_binary_identity,
)

logger = logging.getLogger(__name__)


class WarpScannerWorker:
    """Run the verified ``configstream-tester`` binary in active WARP scan mode."""

    def __init__(self, binary_path: Optional[str] = None):
        self._identity: Optional[BinaryIdentity] = None
        self.binary_path = self._resolve_binary(binary_path)
        self.available = False

        if self.binary_path:
            try:
                self._identity = initialize_binary_identity(self.binary_path)
                self.binary_path = str(self._identity.path)
                self.available = True
            except (OSError, ValueError) as exc:
                logger.error("Warp scanner binary rejected: %s", type(exc).__name__)
                self.binary_path = None

        if self.available:
            logger.debug("WarpScannerWorker initialized with verified tester binary")
        else:
            settings = AppSettings()
            is_ci = os.environ.get("CI") == "true"
            if is_ci and not settings.FORCE_SCANNER:
                logger.info("WarpScannerWorker: Scanner disabled by CI policy.")
            else:
                logger.warning(
                    "WarpScannerWorker: verified Go binary unavailable. Active scanning disabled."
                )

    def _resolve_binary(self, explicit_path: Optional[str]) -> Optional[str]:
        """Resolve the executable without executing it."""

        settings = AppSettings()
        is_ci = os.environ.get("CI") == "true"
        if is_ci and not settings.FORCE_SCANNER:
            logger.info(
                "Scanner disabled in CI. Set FORCE_SCANNER=true to override."
            )
            return None
        if is_ci and settings.FORCE_SCANNER:
            logger.warning(
                "Scanner FORCE ENABLED in CI; UDP egress restrictions may make scans fail."
            )

        if explicit_path and os.path.exists(explicit_path):
            return explicit_path
        if settings.CONFIGSTREAM_TESTER_BIN and os.path.exists(
            settings.CONFIGSTREAM_TESTER_BIN
        ):
            return settings.CONFIGSTREAM_TESTER_BIN

        resolved = shutil.which("configstream-tester")
        if resolved:
            return resolved

        for location in (
            Path.cwd() / "configstream-tester",
            Path.cwd() / "src/go/tester/configstream-tester",
            Path("/usr/local/bin/configstream-tester"),
            Path("/opt/configstream/bin/configstream-tester"),
        ):
            if location.exists():
                return str(location)
        return None

    async def scan_endpoints(
        self, limit: int = 50, timeout: int = 5, max_latency: int = 800
    ) -> List[str]:
        settings = AppSettings()
        if not settings.ALLOW_ACTIVE_SCANNING and not settings.FORCE_SCANNER:
            logger.info(
                "Warp scan skipped: active scanning is disabled (ALLOW_ACTIVE_SCANNING=false)."
            )
            return []
        if not self.available or not self.binary_path or self._identity is None:
            logger.warning("Scan requested but verified binary is unavailable.")
            return []
        if not await asyncio.to_thread(verify_binary_identity, self._identity):
            logger.error("Warp scanner tester binary failed integrity verification")
            self.available = False
            return []

        cmd = [
            self.binary_path,
            "-mode",
            "scan",
            "-limit",
            str(limit),
            "-timeout",
            f"{timeout}s",
            "-workers",
            "100",
        ]

        try:
            logger.info(
                "Starting active WARP scan (target=%d, timeout=%ss)", limit, timeout
            )
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=minimal_subprocess_environment(settings),
            )
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
                logger.error("Scanner binary exited with error code %s", proc.returncode)
                if safe_stderr:
                    logger.error("Scanner stderr: %s", safe_stderr[:1000])
                return []
            if safe_stderr:
                logger.debug("Scanner internals: %s", safe_stderr[:1000])

            raw_output = stdout.decode(errors="replace")
            if not raw_output.strip():
                logger.warning(
                    "Scanner finished successfully but produced no output; network egress may be blocked."
                )
                return []

            clean_ips: list[str] = []
            for line in raw_output.splitlines():
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    logger.debug("Skipping invalid JSON record from scanner")
                    continue
                ip = data.get("ip") if isinstance(data, dict) else None
                latency = data.get("latency", 9999) if isinstance(data, dict) else 9999
                if isinstance(ip, str):
                    try:
                        latency_value = float(latency)
                    except (TypeError, ValueError):
                        continue
                    if latency_value <= max_latency:
                        clean_ips.append(ip)

            logger.info(
                "Active scan completed. Found %d valid IPs (request=%d, max_latency=%dms).",
                len(clean_ips),
                limit,
                max_latency,
            )
            return clean_ips
        except (OSError, ValueError, RuntimeError) as exc:
            logger.error(
                "Active scan execution failed: %s", type(exc).__name__, exc_info=True
            )
            return []
