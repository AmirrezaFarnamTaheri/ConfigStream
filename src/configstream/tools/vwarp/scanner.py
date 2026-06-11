# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
import re
import time
from typing import List, Tuple, Optional

from configstream.async_utils import safe_wait_for
from configstream.config import AppSettings
from configstream.security_validator import SecurityValidator
from .binary import verify_binary

logger = logging.getLogger(__name__)

# Simple IPv4/IPv6 validation pattern for scan output parsing
_IPV4_RE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$"
)

def is_valid_ip(host: str) -> bool:
    """Check if a string looks like a valid IPv4 or IPv6 address."""
    host = host.strip()
    if not host:
        return False
    # IPv4
    if _IPV4_RE.match(host):
        return True
    # IPv6: hex/colon/dot chars only AND at least 2 colons (real IPv6 has 2-7)
    if host.count(":") >= 2 and all(c in "0123456789abcdefABCDEF:." for c in host):
        return True
    return False

async def scan_endpoints(binary_path: Optional[str], rtt_limit: str = "800ms") -> List[Tuple[str, int]]:
    """
    Runs 'vwarp --scan' to harvest unblocked Cloudflare IPs.
    Returns a list of (host, port) tuples.
    """
    settings = AppSettings()
    if not settings.ALLOW_ACTIVE_SCANNING and not settings.FORCE_SCANNER:
        logger.info(
            "Vwarp scan skipped: active scanning is disabled (ALLOW_ACTIVE_SCANNING=false)."
        )
        return []

    if not binary_path or not await verify_binary(binary_path):
        logger.debug("❌ Vwarp binary missing. Cannot scan.")
        return []

    cmd: List[str] = [binary_path, "--scan", "--rtt", rtt_limit]

    try:
        scan_start = time.time()
        logger.info(
            "📡 Starting Vwarp active scanner (rtt_limit=%s, cmd=%s)...",
            rtt_limit,
            " ".join(cmd),
        )
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        
        try:
            if asyncio.current_task() is None:
                stdout, _ = await proc.communicate()
            else:
                stdout, _ = await safe_wait_for(proc.communicate(), timeout=60)
        except asyncio.TimeoutError:
            elapsed = time.time() - scan_start
            logger.warning(
                "Vwarp scan timed out after %.1fs. Killing process.", elapsed
            )
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            return []

        endpoints: List[Tuple[str, int]] = []
        if stdout:
            output_text = stdout.decode(errors="ignore")
            for line in output_text.splitlines():
                if ":" in line and "ms" in line:
                    clean_ep = line.split()[0].strip()
                    host = clean_ep
                    port = 2408  # Default

                    if ":" in clean_ep:
                        if clean_ep.startswith("["):
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
                            parts = clean_ep.rsplit(":", 1)
                            if len(parts) == 2:
                                host = parts[0]
                                try:
                                    port = int(parts[1])
                                except ValueError:
                                    pass
                            else:
                                host = clean_ep

                    if is_valid_ip(host):
                        endpoints.append((host, port))
                    else:
                        logger.debug(
                            "Vwarp scan: skipping non-IP host %s",
                            SecurityValidator.sanitize_log_message(host),
                        )

        elapsed = time.time() - scan_start
        logger.info(
            "✅ Vwarp scan complete: found %d healthy endpoints in %.1fs.",
            len(endpoints),
            elapsed,
        )
        return endpoints

    except Exception as e:
        logger.error(
            "Vwarp scan failed after %.1fs: %s",
            time.time() - scan_start,
            SecurityValidator.sanitize_log_message(str(e)),
        )
        return []
