# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import shutil
import logging
import json
import time
import os
import hashlib
import zipfile
import stat
import sys
import platform
import shlex
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, cast, Tuple, Optional
import httpx

from ..constants import VWARP_SOCKS5_PORT, VWARP_BIND_ADDRESS
from ..async_utils import safe_wait_for

logger = logging.getLogger(__name__)

# Constants for Vwarp binary management
VWARP_VERSION = "v2.1.0"
VWARP_SHA256_AMD64 = "4b971ed3696ed607bf91000f379f6308459fd1dafa1beae14404a8b7ce068cf7"
VWARP_ASSET_AMD64 = "vwarp_linux-amd64.zip"
VWARP_ASSET_ARM64 = "vwarp_linux-arm64.zip"
VWARP_RELEASE_BASE = "https://github.com/voidr3aper-anon/Vwarp/releases/download"


class VwarpTool:
    """
    Controller for the voidr3aper-anon/Vwarp binary.
    Handles scanning, config generation, and transport tunneling.
    """

    def __init__(self) -> None:
        self.binary: Optional[str] = self._find_binary()
        self._tunnel_proc: Optional[asyncio.subprocess.Process] = None
        self._install_lock = asyncio.Lock()
        self._help_text: Optional[str] = None

    @staticmethod
    def _is_supported_platform() -> bool:
        """Vwarp binary is currently only available for Linux."""
        return sys.platform.startswith("linux")

    @staticmethod
    def _platform_asset() -> Tuple[str, Optional[str]]:
        """
        Resolve the appropriate asset and checksum for this platform.
        Returns (asset_name, sha256_or_none).
        """
        machine = (platform.machine() or "").lower()
        if machine in ("x86_64", "amd64"):
            return VWARP_ASSET_AMD64, VWARP_SHA256_AMD64
        if machine in ("aarch64", "arm64"):
            # SHA256 unknown for arm64 unless provided via env override.
            return VWARP_ASSET_ARM64, None
        # Default to amd64 asset for unknown Linux machines.
        return VWARP_ASSET_AMD64, VWARP_SHA256_AMD64

    @staticmethod
    def _get_download_spec() -> Tuple[str, Optional[str], str]:
        """
        Resolve download URL and checksum.
        Environment overrides:
        - VWARP_VERSION
        - VWARP_URL
        - VWARP_SHA256
        """
        version = os.environ.get("VWARP_VERSION", VWARP_VERSION)
        env_url = os.environ.get("VWARP_URL", "").strip()
        env_sha = os.environ.get("VWARP_SHA256", "").strip()
        asset_name, default_sha = VwarpTool._platform_asset()

        if env_url:
            url = env_url
        else:
            url = f"{VWARP_RELEASE_BASE}/{version}/{asset_name}"

        checksum = env_sha or default_sha
        return url, checksum or None, version

    def _find_binary(self) -> Optional[str]:
        """Locates the vwarp binary in PATH or common locations."""
        # 1. Check PATH
        binary = shutil.which("vwarp")
        if binary:
            return binary

        # 2. Check user local bin
        home = Path.home()
        local_bin = home / ".local" / "bin" / "vwarp"
        if local_bin.exists() and os.access(local_bin, os.X_OK):
            return str(local_bin)

        # 3. Check fallback paths
        possible_paths = ["/usr/local/bin/vwarp", "/opt/vwarp/vwarp", "./vwarp"]
        for p in possible_paths:
            if Path(p).exists() and os.access(p, os.X_OK):
                return p

        return None

    async def ensure_installed(self) -> bool:
        """
        Ensures Vwarp is installed. Downloads if missing.
        Returns True if installed/available, False otherwise.
        """
        if not self._is_supported_platform():
            logger.info("Vwarp install skipped: unsupported platform.")
            return False
        if self.binary and Path(self.binary).exists():
            return True

        async with self._install_lock:
            # Re-check inside lock
            self.binary = self._find_binary()
            if self.binary:
                return True

            url, checksum, version = self._get_download_spec()
            logger.info(
                f"Vwarp binary not found. Attempting to download {version}..."
            )

            try:
                # Determine install location
                # Prefer ~/.local/bin, create if needed
                home = Path.home()
                install_dir = home / ".local" / "bin"
                install_dir.mkdir(parents=True, exist_ok=True)
                target_path = install_dir / "vwarp"

                # Check write permissions
                if not os.access(install_dir, os.W_OK):
                    # Fallback to current directory or /tmp
                    install_dir = Path("/tmp/configstream-bin")
                    install_dir.mkdir(parents=True, exist_ok=True)
                    target_path = install_dir / "vwarp"
                    logger.warning(
                        f"Cannot write to ~/.local/bin, installing to {target_path}"
                    )

                logger.info(f"Downloading Vwarp from {url}")

                async with httpx.AsyncClient(
                    follow_redirects=True, timeout=60.0
                ) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    content = resp.content

                # Verify Checksum (if available)
                if checksum:
                    digest = hashlib.sha256(content).hexdigest()
                    if digest != checksum:
                        if os.environ.get("VWARP_SKIP_CHECKSUM", "").lower() in (
                            "1",
                            "true",
                            "yes",
                        ):
                            logger.warning(
                                "Vwarp checksum mismatch but VWARP_SKIP_CHECKSUM=true; "
                                "continuing install."
                            )
                        else:
                            logger.error(
                                f"Vwarp checksum mismatch! Expected {checksum}, got {digest}"
                            )
                            return False
                else:
                    logger.warning(
                        "Vwarp checksum not provided for this platform; "
                        "set VWARP_SHA256 to enforce verification."
                    )

                # Extract
                with zipfile.ZipFile(BytesIO(content)) as zf:
                    # Find the vwarp binary in the zip using exact filename match
                    vwarp_member_info = None
                    for member_info in zf.infolist():
                        if (
                            not member_info.is_dir()
                            and Path(member_info.filename).name == "vwarp"
                        ):
                            vwarp_member_info = member_info
                            break

                    if not vwarp_member_info:
                        logger.error("Vwarp binary not found in zip archive")
                        return False

                    # Extract to target path
                    with (
                        zf.open(vwarp_member_info) as source,
                        open(target_path, "wb") as target,
                    ):
                        shutil.copyfileobj(source, target)

                # Make executable
                st = os.stat(target_path)
                os.chmod(target_path, st.st_mode | stat.S_IEXEC)

                self.binary = str(target_path)
                self._help_text = None

                # Verify it runs
                proc = await asyncio.create_subprocess_exec(
                    self.binary,
                    "version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()

                if proc.returncode == 0:
                    logger.info(f"✅ Vwarp successfully installed to {self.binary}")
                    return True
                else:
                    logger.error(
                        f"Vwarp installed but failed execution check (code {proc.returncode})"
                    )
                    return False

            except Exception as e:
                logger.error(f"Failed to install Vwarp: {e}")
                return False

    async def is_available(self) -> bool:
        """Quick health check."""
        if self.binary:
            if not self._is_supported_platform():
                logger.debug(
                    "Vwarp binary found on unsupported platform; skipping platform gate."
                )
                return True
            if Path(self.binary).exists():
                if await self._verify_binary():
                    return True
                logger.warning("Existing Vwarp binary failed health check. Reinstalling.")
                self.binary = None
                self._help_text = None

        if not self._is_supported_platform():
            logger.debug("Vwarp unavailable: unsupported platform.")
            return False

        # Attempt installation if missing
        return await self.ensure_installed()

    async def _verify_binary(self) -> bool:
        """Verify the existing binary executes properly."""
        if not self.binary:
            return False
        try:
            proc = await asyncio.create_subprocess_exec(
                self.binary,
                "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                return True
            if stderr:
                logger.error(f"Vwarp version check failed: {stderr.decode(errors='ignore')}")
            elif stdout:
                logger.error(f"Vwarp version check failed: {stdout.decode(errors='ignore')}")
            return False
        except Exception as exc:
            logger.error(f"Vwarp version check error: {exc}")
            return False

    async def _get_help_text(self) -> str:
        """Fetch and cache help text to detect supported flags."""
        if self._help_text is not None:
            return self._help_text
        if not self.binary:
            self._help_text = ""
            return self._help_text
        for args in (["--help"], ["-h"]):
            try:
                proc = await asyncio.create_subprocess_exec(
                    self.binary,
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                text = (stdout or b"") + (stderr or b"")
                if text:
                    self._help_text = text.decode(errors="ignore")
                    return self._help_text
            except Exception:
                continue
        self._help_text = ""
        return self._help_text

    async def _build_tunnel_command(self, bind_addr: str, port: int) -> List[str]:
        """Build the best available tunnel command for the detected Vwarp version."""
        if not self.binary:
            return []

        bind_value = f"{bind_addr}:{port}"
        env_args = os.environ.get("VWARP_TUNNEL_ARGS", "").strip()
        if env_args:
            expanded = env_args.replace("{bind}", bind_value)
            return [self.binary] + shlex.split(expanded)

        help_text = await self._get_help_text()
        if "--bind" in help_text:
            return [self.binary, "--bind", bind_value]
        if "--socks5" in help_text:
            return [self.binary, "--socks5", bind_value]
        if "--socks" in help_text:
            return [self.binary, "--socks", bind_value]
        if "--listen" in help_text:
            return [self.binary, "--listen", bind_value]

        # Fallback to historical flag
        return [self.binary, "--bind", bind_value]

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

        if not await self.is_available() or not self.binary:
            logger.debug("❌ Vwarp binary missing. Cannot scan.")
            return []

        # Command: vwarp --scan --rtt 800ms --verbose
        cmd: List[str] = [self.binary, "--scan", "--rtt", rtt_limit]

        try:
            logger.info("📡 Starting Vwarp active scanner...")
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            # Give it 30 seconds max to find IPs
            try:
                if asyncio.current_task() is None:
                    stdout, _ = await proc.communicate()
                else:
                    stdout, _ = await safe_wait_for(proc.communicate(), timeout=30)
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
        if not await self.is_available() or not self.binary:
            return {}

        cmd: List[str] = [self.binary, "--export-singbox", "--masque-preset", preset]
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
            # [FIX] Check if process died while waiting
            if self._tunnel_proc and self._tunnel_proc.returncode is not None:
                logger.error(
                    f"Vwarp process died with code {self._tunnel_proc.returncode} while waiting for port."
                )
                try:
                    stdout, stderr = await self._tunnel_proc.communicate()
                    if stdout:
                        logger.error(f"Vwarp stdout: {stdout.decode(errors='ignore')}")
                    if stderr:
                        logger.error(f"Vwarp stderr: {stderr.decode(errors='ignore')}")
                except Exception:
                    pass
                return False

            try:
                # Use asyncio to avoid blocking the event loop
                reader, writer = await safe_wait_for(
                    asyncio.open_connection(probe_host, port), timeout=1
                )
                writer.close()
                await writer.wait_closed()
                return True
            except (OSError, asyncio.TimeoutError, ConnectionRefusedError) as e:
                # Log only if debug is enabled to avoid spam
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Vwarp port check failed (retrying): {e}")
                # Throttling: wait a bit longer or use exponential backoff to reduce CPU/Net load
                await asyncio.sleep(1.0)
        return False

    async def start_tunnel(
        self, bind_addr: str = VWARP_BIND_ADDRESS, port: int = VWARP_SOCKS5_PORT
    ) -> bool:
        """
        Starts the Vwarp SOCKS5 tunnel in the background.
        """
        if not await self.is_available() or not self.binary:
            return False

        if self._tunnel_proc:
            # Already running
            return True

        cmd = await self._build_tunnel_command(bind_addr, port)
        if not cmd:
            logger.error("Vwarp tunnel command could not be constructed.")
            return False
        try:
            logger.info(f"🚀 Starting Vwarp SOCKS5 Tunnel on {bind_addr}:{port}...")
            # Capture stdout/stderr for debugging if it fails
            self._tunnel_proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Check for immediate failure and capture logs
            await asyncio.sleep(0.5)
            if self._tunnel_proc.returncode is not None:
                stdout, stderr = await self._tunnel_proc.communicate()
                if stdout:
                    logger.error(f"Vwarp stdout: {stdout.decode(errors='ignore')}")
                if stderr:
                    logger.error(f"Vwarp stderr: {stderr.decode(errors='ignore')}")
                return False

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
                            stdout, stderr = await safe_wait_for(
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
                    await safe_wait_for(self._tunnel_proc.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    self._tunnel_proc.kill()
            except ProcessLookupError:
                pass
            except Exception as e:
                logger.warning(f"Error stopping Vwarp tunnel: {e}")
            finally:
                self._tunnel_proc = None
