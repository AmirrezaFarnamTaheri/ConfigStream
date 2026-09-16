# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import ipaddress
import logging
import time
from typing import List, Tuple, Optional

from configstream.async_utils import safe_wait_for
from configstream.config import AppSettings
from configstream.security_validator import SecurityValidator
from .binary import minimal_vwarp_environment, verify_binary

logger = logging.getLogger(__name__)

_DEFAULT_SCAN_PORT = 2408


def is_valid_ip(host: str) -> bool:
    """Return whether *host* is a syntactically valid IPv4 or IPv6 address."""
    candidate = host.strip()
    if not candidate:
        return False
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        return False
    return True


def _parse_endpoint(value: str) -> Optional[Tuple[str, int]]:
    """Parse one scanner endpoint without confusing IPv6 hextets with ports."""
    candidate = value.strip()
    if not candidate:
        return None

    if candidate.startswith("["):
        bracket_end = candidate.find("]")
        if bracket_end <= 1:
            return None
        host = candidate[1:bracket_end]
        rest = candidate[bracket_end + 1 :]
        if not rest:
            port = _DEFAULT_SCAN_PORT
        elif rest.startswith(":") and rest[1:].isdigit():
            port = int(rest[1:])
        else:
            return None
    elif is_valid_ip(candidate):
        host = candidate
        port = _DEFAULT_SCAN_PORT
    else:
        host, separator, port_text = candidate.rpartition(":")
        if (
            not separator
            or not host
            or not port_text.isdigit()
            or not is_valid_ip(host)
        ):
            return None
        port = int(port_text)

    if not is_valid_ip(host) or not 1 <= port <= 65535:
        return None
    return host, port


async def _kill_and_reap(proc: asyncio.subprocess.Process) -> None:
    """Kill a scanner child if needed and always attempt to reap it."""
    if proc.returncode is None:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
    try:
        await safe_wait_for(proc.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        logger.error("Vwarp scan process could not be reaped after kill.")
    except (OSError, RuntimeError) as exc:
        logger.warning(
            "Vwarp scan process cleanup failed: %s",
            SecurityValidator.sanitize_log_message(str(exc)),
        )


async def scan_endpoints(
    binary_path: Optional[str], rtt_limit: str = "800ms"
) -> List[Tuple[str, int]]:
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
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=minimal_vwarp_environment(),
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
            await _kill_and_reap(proc)
            return []
        except asyncio.CancelledError:
            await _kill_and_reap(proc)
            raise

        endpoints: List[Tuple[str, int]] = []
        if stdout:
            output_text = stdout.decode(errors="ignore")
            for line in output_text.splitlines():
                if ":" not in line or "ms" not in line:
                    continue
                raw_endpoint = line.split()[0].strip()
                endpoint = _parse_endpoint(raw_endpoint)
                if endpoint is not None:
                    endpoints.append(endpoint)
                else:
                    logger.debug(
                        "Vwarp scan: skipping invalid endpoint %s",
                        SecurityValidator.sanitize_log_message(raw_endpoint),
                    )

        elapsed = time.time() - scan_start
        logger.info(
            "✅ Vwarp scan complete: found %d healthy endpoints in %.1fs.",
            len(endpoints),
            elapsed,
        )
        return endpoints

    except asyncio.CancelledError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        logger.error(
            "Vwarp scan failed after %.1fs: %s",
            time.time() - scan_start,
            SecurityValidator.sanitize_log_message(str(exc)),
        )
        return []
