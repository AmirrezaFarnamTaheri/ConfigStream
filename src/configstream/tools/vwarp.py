# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import shutil
import copy
import logging
import json
import time
import os
from datetime import datetime, timezone
import hashlib
import zipfile
import stat
import sys
import platform
import shlex
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
import re
import httpx

from ..constants import VWARP_SOCKS5_PORT, VWARP_BIND_ADDRESS
from ..async_utils import safe_wait_for
from ..security_validator import SecurityValidator

logger = logging.getLogger(__name__)

# Simple IPv4/IPv6 validation pattern for scan output parsing
_IPV4_RE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$"
)


def _is_valid_ip(host: str) -> bool:
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


# Constants for Vwarp binary management
# Latest: v2.2.2 (2025-12-16) - https://github.com/voidr3aper-anon/Vwarp/releases
# v2.2.1+ supports full JSON config (JunkInterval, masque.enabled, masque.preferred)
VWARP_VERSION = "v2.2.2"
VWARP_SHA256_AMD64 = "90619d5e8ceec07fe09b967904f490d5a45f812951f7fae4cb375b60207b6312"
VWARP_ASSET_AMD64 = "vwarp_linux-amd64.zip"
VWARP_ASSET_ARM64 = "vwarp_linux-arm64.zip"
VWARP_RELEASE_BASE = "https://github.com/voidr3aper-anon/Vwarp/releases/download"

# Default Cloudflare WARP endpoint
DEFAULT_WARP_ENDPOINT = "162.159.192.1:2408"

# Psiphon country codes supported by vwarp (--cfon --country <CODE>)
# Source: official vwarp CONFIG_FORGE.md
PSIPHON_COUNTRY_CODES = frozenset(
    {
        # Americas
        "US",
        "CA",
        "BR",
        # Europe
        "GB",
        "DE",
        "FR",
        "IT",
        "ES",
        "NL",
        "SE",
        "NO",
        "DK",
        "FI",
        "CH",
        "AT",
        "BE",
        "IE",
        "PT",
        "PL",
        "CZ",
        "HU",
        "RO",
        "BG",
        "HR",
        "EE",
        "LV",
        "SK",
        "RS",
        # Asia-Pacific
        "JP",
        "SG",
        "AU",
        "IN",
    }
)

# MASQUE noize presets aligned with official vwarp presets
# Keys map to --masque-noize-preset values and config file Jc levels
MASQUE_NOIZE_PRESETS: Dict[str, Dict[str, Any]] = {
    "light": {
        "Jc": 2,
        "Jmin": 32,
        "Jmax": 64,
        "JcBeforeHS": 2,
        "JcDuringHS": 0,
        "JcAfterHS": 0,
        "JunkInterval": 10000000,
        "HandshakeDelay": 20000000,
        "MimicProtocol": "quic",
        "FragmentInitial": False,
        "RandomPadding": False,
    },
    "medium": {
        "Jc": 3,
        "Jmin": 40,
        "Jmax": 80,
        "JcBeforeHS": 2,
        "JcDuringHS": 1,
        "JcAfterHS": 0,
        "JunkInterval": 15000000,
        "HandshakeDelay": 25000000,
        "MimicProtocol": "https",
        "PaddingMin": 8,
        "PaddingMax": 32,
        "RandomPadding": True,
    },
    "heavy": {
        "Jc": 6,
        "Jmin": 32,
        "Jmax": 128,
        "JcBeforeHS": 3,
        "JcDuringHS": 2,
        "JcAfterHS": 1,
        "JunkInterval": 25000000,
        "HandshakeDelay": 75000000,
        "MimicProtocol": "https",
        "FragmentInitial": True,
        "FragmentSize": 512,
        "PaddingMin": 16,
        "PaddingMax": 64,
        "RandomPadding": True,
        "SNIFragmentation": True,
    },
    "gfw": {
        "Jc": 15,
        "Jmin": 30,
        "Jmax": 120,
        "JcBeforeHS": 3,
        "JcAfterI1": 2,
        "JcDuringHS": 5,
        "JcAfterHS": 3,
        "JunkInterval": 20000000,
        "HandshakeDelay": 30000000,
        "MimicProtocol": "https",
        "FragmentInitial": True,
        "FragmentSize": 512,
        "PaddingMin": 16,
        "PaddingMax": 64,
        "RandomPadding": True,
        "SNIFragmentation": True,
        "CustomHeaders": True,
        "MimicTLS": True,
    },
}

# AtomicNoize presets for WireGuard obfuscation
ATOMICNOIZE_PRESETS: Dict[str, Dict[str, Any]] = {
    "light": {
        "I1": "<b 0c0d0e0f>",
        "Jc": 10,
        "Jmin": 40,
        "Jmax": 90,
        "JcAfterI1": 1,
        "JcBeforeHS": 1,
        "JcAfterHS": 1,
        "JunkInterval": 100000000,
        "HandshakeDelay": 10000000,
        "AllowZeroSize": False,
    },
    "medium": {
        "I1": "<b 0c0d0e0f>",
        "I3": "<b 040506>",
        "Jc": 25,
        "Jmin": 40,
        "Jmax": 90,
        "JcAfterI1": 2,
        "JcBeforeHS": 3,
        "JcAfterHS": 2,
        "JunkInterval": 150000000,
        "HandshakeDelay": 25000000,
        "AllowZeroSize": True,
    },
    "heavy": {
        "I1": "<b 0c0d0e0f>",
        "I3": "<b 040506>",
        "I4": "<b 0708>",
        "I5": "<b 09>",
        "Jc": 85,
        "Jmin": 40,
        "Jmax": 90,
        "JcAfterI1": 3,
        "JcBeforeHS": 5,
        "JcAfterHS": 4,
        "JunkInterval": 150000000,
        "HandshakeDelay": 25000000,
        "AllowZeroSize": True,
    },
}


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
        self._config_path: Optional[Path] = None
        self._config_owned: bool = False
        self._last_failure_reason: Optional[str] = None
        self._last_failure_details: Optional[str] = None

    @staticmethod
    def validate_warp_key(key: str) -> bool:
        """Validates a WARP key structure."""
        if not key:
            return False
        if not re.match(r"^[a-zA-Z0-9+/=_-]{40,}$", key):
            logger.warning("Invalid WARP key format")
            return False
        return True

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
            platform_hint = (
                "Use USE_VWARP_TUNNEL=false for non-Linux environments."
                if sys.platform == "win32"
                else "Vwarp binary is Linux-only."
            )
            logger.info(
                "Vwarp install skipped: unsupported platform (%s). %s",
                sys.platform,
                platform_hint,
            )
            return False
        if self.binary and Path(self.binary).exists():
            return True

        async with self._install_lock:
            # Re-check inside lock
            self.binary = self._find_binary()
            if self.binary:
                return True

            url, checksum, version = self._get_download_spec()
            logger.info(f"Vwarp binary not found. Attempting to download {version}...")

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
                    install_dir = Path("/tmp/configstream-bin")  # nosec
                    install_dir.mkdir(parents=True, exist_ok=True)
                    target_path = install_dir / "vwarp"
                    logger.warning(
                        f"Cannot write to ~/.local/bin, installing to {target_path}"
                    )

                logger.info(
                    f"Downloading Vwarp from {SecurityValidator.sanitize_log_message(url)}"
                )

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
                                "Vwarp checksum mismatch! Expected %s, got %s. "
                                "Set VWARP_SKIP_CHECKSUM=true to bypass, or "
                                "VWARP_SHA256=%s to update.",
                                checksum,
                                digest,
                                digest,
                            )
                            return False
                else:
                    logger.warning(
                        "Vwarp checksum not provided for this platform (%s); "
                        "set VWARP_SHA256 to enforce verification.",
                        platform.machine() or "unknown",
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
                        members = [m.filename for m in zf.infolist()[:10]]
                        logger.error(
                            "Vwarp binary not found in zip archive. "
                            "Archive contents (first 10): %s",
                            members,
                        )
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
                logger.warning(
                    "Existing Vwarp binary failed health check. Reinstalling."
                )
                self.binary = None
                self._help_text = None

        if not self._is_supported_platform():
            logger.info(
                "Vwarp unavailable: unsupported platform (%s). "
                "Set USE_VWARP_TUNNEL=false to disable.",
                sys.platform,
            )
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
                logger.error(
                    f"Vwarp version check failed: {stderr.decode(errors='ignore')}"
                )
            elif stdout:
                logger.error(
                    f"Vwarp version check failed: {stdout.decode(errors='ignore')}"
                )
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
            except Exception:  # nosec
                continue
        self._help_text = ""
        return self._help_text

    async def _build_tunnel_command(
        self,
        bind_addr: str,
        port: int,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Build the best available tunnel command for the detected Vwarp version."""
        if not self.binary:
            return []

        bind_value = f"{bind_addr}:{port}"
        env_args = os.environ.get("VWARP_TUNNEL_ARGS", "").strip()
        if env_args:
            expanded = env_args.replace("{bind}", bind_value)
            return [self.binary] + shlex.split(expanded)

        config_path, extra_flags = await self._prepare_tunnel_config(
            bind_addr, port, config_override=config_override
        )
        if config_path:
            return [self.binary, "--config", str(config_path)] + extra_flags

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

    def _get_default_config(self) -> Dict[str, Any]:
        return {
            "version": "1.0",
            # bind will be set dynamically
            "endpoint": "162.159.192.1:2408",
            "dns": "1.1.1.1",
            "wireguard": {
                "enabled": True,
                "reserved": "1,2,3",
                "fwmark": 0,
                "atomicnoize": {
                    "I1": "<b 0c0d0e0f>",
                    "I3": "<b 040506>",
                    "I4": "<b 0708>",
                    "I5": "<b 09>",
                    "S1": 1,
                    "S2": 2,
                    "Jc": 8,
                    "Jmin": 40,
                    "Jmax": 90,
                    "JcAfterI1": 3,
                    "JcBeforeHS": 5,
                    "JcAfterHS": 4,
                    "JunkInterval": 15000000,
                    "AllowZeroSize": False,
                    "HandshakeDelay": 5000000,
                },
            },
            "masque": {
                "enabled": False,
                "preferred": False,
                "config": {
                    "i1": "<b 0d0a0d0a>",
                    "i3": "<b 0102>",
                    "i4": "<b 030405>",
                    "i5": "<b 060708>",
                    "fragment_size": 0,
                    "fragment_initial": False,
                    "FragmentDelay": 500000,
                    "PaddingMin": 0,
                    "PaddingMax": 0,
                    "RandomPadding": False,
                    "Jc": 8,
                    "Jmin": 30,
                    "Jmax": 120,
                    "JcBeforeHS": 3,
                    "JcAfterI1": 2,
                    "JcDuringHS": 5,
                    "JcAfterHS": 3,
                    "JunkInterval": 20000000,
                    "JunkRandom": True,
                    "MimicProtocol": "quic",
                    "CustomWrapper": True,
                    "HandshakeDelay": 30000000,
                    "PacketDelay": 5000000,
                    "RandomDelay": True,
                    "DelayMin": 2000000,
                    "DelayMax": 15000000,
                    "SNIFragmentation": False,
                    "SNIFragment": 32,
                    "FakeALPN": ["h2", "http/1.1"],
                    "ReversedOrder": False,
                    "DuplicatePackets": False,
                    "AllowZeroSize": True,
                    "UseTimestamp": False,
                    "UseNonce": True,
                    "RandomizeInitial": True,
                    "FakeLoss": 0.05,
                },
            },
            "psiphon": {"enabled": False, "country": "US"},
            "metadata": {
                "name": "sample-working-generated",
                "description": "Auto-generated from ConfigStream based on sample-working.json",
                "author": "ConfigStream",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    async def _prepare_tunnel_config(
        self,
        bind_addr: str,
        port: int,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[Path], List[str]]:
        """
        Build a temporary config file for Vwarp using the Unified Configuration format.
        Returns (path, extra_flags).
        """
        env_path = os.environ.get("VWARP_CONFIG_PATH", "").strip()
        if env_path:
            path = Path(env_path)
            if path.exists():
                self._config_path = path
                self._config_owned = False
                logger.info(f"Using Vwarp config from path: {path}")
                # We assume the user knows what they are doing with flags if providing a custom file.
                # However, to be safe, we check if we should add --masque based on env.
                extra = self._config_extra_flags({})
                return path, extra
            logger.error("VWARP_CONFIG_PATH set but file does not exist.")
            # Fallback to generation

        # Start with default config
        vwarp_config = self._get_default_config()

        # Apply Overrides
        vwarp_config["bind"] = f"{bind_addr}:{port}"

        # Env Overrides
        env_endpoint = os.environ.get("VWARP_ENDPOINT", "").strip()
        if env_endpoint:
            vwarp_config["endpoint"] = env_endpoint

        env_dns = os.environ.get("VWARP_DNS", "").strip()
        if env_dns:
            vwarp_config["dns"] = env_dns

        env_test_url = os.environ.get("VWARP_TEST_URL", "").strip()
        if env_test_url:
            vwarp_config["test_url"] = env_test_url

        env_key = os.environ.get("WARP_LICENSE_KEY", "").strip()
        if env_key:
            vwarp_config["key"] = env_key

        # Masque & Psiphon Overrides
        if "VWARP_MASQUE_ENABLED" in os.environ:
            vwarp_config["masque"]["enabled"] = os.environ.get(
                "VWARP_MASQUE_ENABLED", ""
            ).lower() in ("1", "true", "yes")

        if "PSIPHON_ENABLED" in os.environ:
            vwarp_config["psiphon"]["enabled"] = os.environ.get(
                "PSIPHON_ENABLED", ""
            ).lower() in ("1", "true", "yes")

        env_psiphon_country = os.environ.get("PSIPHON_COUNTRY", "").strip()
        if env_psiphon_country:
            vwarp_config["psiphon"]["country"] = env_psiphon_country

        # Config Override (Programmatic) with Deep Merge
        if config_override:
            for key, value in config_override.items():
                # Deep merge for specific sections to preserve defaults
                if (
                    key in ["masque", "wireguard", "psiphon"]
                    and isinstance(value, dict)
                    and isinstance(vwarp_config.get(key), dict)
                ):
                    target = vwarp_config[key]
                    for subk, subv in value.items():
                        # Level 2 merge for 'config' (masque) and 'atomicnoize' (wireguard)
                        if (
                            subk == "config"
                            and isinstance(subv, dict)
                            and isinstance(target.get("config"), dict)
                        ):
                            target["config"].update(subv)
                        elif (
                            subk == "atomicnoize"
                            and isinstance(subv, dict)
                            and isinstance(target.get("atomicnoize"), dict)
                        ):
                            target["atomicnoize"].update(subv)
                        else:
                            target[subk] = subv
                else:
                    vwarp_config[key] = value

            # Ensure bind matches if overridden but we enforce it
            vwarp_config["bind"] = f"{bind_addr}:{port}"

        # JSON Override (Env)
        env_json = os.environ.get("VWARP_CONFIG_JSON", "").strip()
        if env_json:
            try:
                parsed = json.loads(env_json)
                if isinstance(parsed, dict):
                    vwarp_config.update(parsed)
                    # Ensure bind is preserved unless user explicitly wants to break it (unlikely)
                    vwarp_config["bind"] = f"{bind_addr}:{port}"
            except json.JSONDecodeError:
                logger.warning("VWARP_CONFIG_JSON is invalid JSON; ignoring.")

        # Determine Extra Flags
        extra_flags: List[str] = []

        # Check if we should enable masque via flag (overrides config)
        # Docs: "vwarp --config ... --masque"
        # If config["masque"]["enabled"] is False, but we want it, add flag?
        # Default sample has enabled=False. So we likely need --masque if we want masque.
        # But wait, user said "SET VWARP TRUE". Usually implies using it.
        # Let's check VWARP_FORCE_MASQUE or similar.

        force_masque = os.environ.get("VWARP_FORCE_MASQUE", "").lower() in (
            "1",
            "true",
            "yes",
        )
        # If not explicitly forced, do we default to adding --masque?
        # The quick start says: "vwarp --config my-config.json --masque".
        # So commonly --masque is used.
        # Let's add it if force_masque OR if we suspect we want it.
        # Safe bet: If config doesn't enable it, add --masque?
        # No, flags override config.

        if force_masque:
            extra_flags.append("--masque")

        self._log_config("generated", vwarp_config)
        path_result, _ = self._write_temp_config(vwarp_config)

        return path_result, extra_flags

    @staticmethod
    def _config_extra_flags(config: Dict[str, Any]) -> List[str]:
        """Determine any extra CLI flags required by the config."""
        force_masque = os.environ.get("VWARP_FORCE_MASQUE", "").lower() in (
            "1",
            "true",
            "yes",
        )
        if force_masque:
            return ["--masque"]
        masque_cfg = config.get("masque")
        if isinstance(masque_cfg, dict) and masque_cfg.get("enabled") is True:
            return ["--masque"]
        return []

    @staticmethod
    def _sanitize_config_for_binary(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove config fields rejected by vwarp v2.1.x (schema divergence).
        v2.2.1+ supports full config; use VWARP_VERSION=v2.1.0 to force sanitization.
        """
        out = copy.deepcopy(config)
        # wireguard.atomicnoize: remove JunkInterval (binary uses different schema)
        wg = out.get("wireguard")
        if isinstance(wg, dict):
            ano = wg.get("atomicnoize")
            if isinstance(ano, dict):
                ano = dict(ano)
                ano.pop("JunkInterval", None)
                out["wireguard"] = dict(wg)
                out["wireguard"]["atomicnoize"] = ano
        # masque: remove enabled/preferred (binary uses --masque CLI flag instead)
        masque = out.get("masque")
        if isinstance(masque, dict):
            masque = dict(masque)
            masque.pop("enabled", None)
            masque.pop("preferred", None)
            out["masque"] = masque
        return out

    def _write_temp_config(
        self, config: Dict[str, Any]
    ) -> Tuple[Optional[Path], List[str]]:
        tmp_dir = Path(tempfile.gettempdir())
        tmp_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix="vwarp-config-", suffix=".json")
        os.close(fd)
        tmp_path = Path(tmp_name)

        # Sanitize config for Vwarp binary compatibility
        write_config = copy.deepcopy(config)
        write_config.pop("version", None)
        write_config.pop("metadata", None)
        write_config.pop(
            "test_url", None
        )  # Explicitly remove test_url to avoid parse errors
<<<<<<< Updated upstream

        # v2.2.1+ supports full config; v2.1.x rejects JunkInterval, masque.enabled/preferred
        version = os.environ.get("VWARP_VERSION", VWARP_VERSION)
        if version < "v2.2.1":
            write_config = self._sanitize_config_for_binary(write_config)
=======
>>>>>>> Stashed changes

        # Flatten Masque if needed
        if "masque" in write_config:
            if isinstance(write_config["masque"], dict):
                pass  # Keep unified structure

        # Keep Psiphon enabled flag

        try:
            tmp_path.write_text(json.dumps(write_config), encoding="utf-8")
        except OSError as exc:
            logger.error(f"Failed to write Vwarp config: {exc}")
            return None, []

        self._config_path = tmp_path
        self._config_owned = True
        extra_flags = self._config_extra_flags(config)
        return tmp_path, extra_flags

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
            scan_start = time.time()
            logger.info(
                "📡 Starting Vwarp active scanner (rtt_limit=%s, cmd=%s)...",
                rtt_limit,
                " ".join(cmd),
            )
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            # Give it 60 seconds max to find IPs (CI environments need more time)
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

                        if _is_valid_ip(host):
                            endpoints.append((host, port))
                        else:
                            logger.debug("Vwarp scan: skipping non-IP host %r", host)

            elapsed = time.time() - scan_start
            logger.info(
                "✅ Vwarp scan complete: found %d healthy endpoints in %.1fs.",
                len(endpoints),
                elapsed,
            )
            return endpoints

        except Exception as e:
            logger.error(
                "Vwarp scan failed after %.1fs: %s", time.time() - scan_start, e
            )
            return []

    @staticmethod
    def build_vwarp_config(
        bind: str = "127.0.0.1:8086",
        endpoint: str = DEFAULT_WARP_ENDPOINT,
        key: Optional[str] = None,
        dns: str = "1.1.1.1",
        masque_preset: Optional[str] = None,
        atomicnoize_preset: Optional[str] = None,
        psiphon_country: Optional[str] = None,
        proxy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Builds a complete vwarp JSON configuration file.

        Aligns with official vwarp CONFIG_FORGE.md format:
        - ``masque_preset``: light | moderate | heavy | gfw
        - ``atomicnoize_preset``: light | moderate | heavy
        - ``psiphon_country``: ISO country code (US, DE, JP, etc.)
        - ``proxy``: SOCKS5 upstream proxy (e.g. socks5://127.0.0.1:1080)
        """
        config: Dict[str, Any] = {
            "bind": bind,
            "endpoint": endpoint,
            "dns": dns,
        }
        if key:
            config["key"] = key
        if proxy:
            config["proxy"] = proxy

        # MASQUE configuration
        if masque_preset:
            preset_data = MASQUE_NOIZE_PRESETS.get(masque_preset, {})
            config["masque"] = {
                "enabled": True,
                "preferred": True,
                "config": dict(preset_data),
            }
        else:
            config["masque"] = {"enabled": False}

        # WireGuard + AtomicNoize configuration
        atomicnoize_data: Dict[str, Any] = {}
        if atomicnoize_preset:
            atomicnoize_data = dict(ATOMICNOIZE_PRESETS.get(atomicnoize_preset, {}))
        config["wireguard"] = {
            "enabled": True,
            "reserved": "0,0,0",
            "atomicnoize": atomicnoize_data if atomicnoize_data else {},
        }

        # Psiphon integration
        if psiphon_country:
            country = psiphon_country.upper()
            if country not in PSIPHON_COUNTRY_CODES:
                logger.warning(
                    "Psiphon country '%s' not in known supported list; "
                    "proceeding anyway.",
                    country,
                )
            config["psiphon"] = {"enabled": True, "country": country}
        else:
            config["psiphon"] = {"enabled": False, "country": "US"}

        return config

    async def generate_masque_config(self, preset: str = "gfw") -> Dict[str, Any]:
        """
        Generates a vwarp MASQUE configuration dict for the given preset.

        Unlike earlier versions that tried non-existent CLI flags, this
        builds the config dict directly using the official vwarp JSON
        format documented in CONFIG_FORGE.md.
        """
        return self.build_vwarp_config(masque_preset=preset)

    async def _wait_for_port(self, host: str, port: int, timeout: int = 45) -> bool:
        """Polls the given host:port until it accepts connections."""
        probe_host = host
        if host in ("0.0.0.0", "::", ""):  # nosec
            probe_host = "127.0.0.1"

        start = time.time()
        while time.time() - start < timeout:
            # Check if process died while waiting
            if self._tunnel_proc and self._tunnel_proc.returncode is not None:
                logger.error(
                    f"Vwarp process died with code {self._tunnel_proc.returncode} while waiting for port."
                )
                try:
                    stdout, stderr = await self._tunnel_proc.communicate()
                    combined = (stdout or b"") + b"\n" + (stderr or b"")
                    details = combined.decode(errors="ignore")
                    if stdout:
                        logger.error(f"Vwarp stdout: {stdout.decode(errors='ignore')}")
                    if stderr:
                        logger.error(f"Vwarp stderr: {stderr.decode(errors='ignore')}")
                    if details:
                        self._record_failure(self._classify_failure(details), details)
                except Exception:  # nosec
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
        self,
        bind_addr: str = VWARP_BIND_ADDRESS,
        port: int = VWARP_SOCKS5_PORT,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Starts the Vwarp SOCKS5 tunnel in the background.
        """
        if not await self.is_available() or not self.binary:
            return False

        if self._tunnel_proc:
            # Already running
            return True

        async def attempt(
            label: str, override: Optional[Dict[str, Any]] = None
        ) -> bool:
            if override:
                logger.info(f"Retrying Vwarp tunnel with fallback config: {label}")
            return await self._start_tunnel_once(bind_addr, port, override)

        success = await attempt("primary", config_override)
        if success:
            return True

        # Fallback: force a minimal config (no test_url which causes parse errors)
        fallback_enabled = os.environ.get("VWARP_RETRY_FALLBACK", "").lower() not in (
            "0",
            "false",
            "no",
        )
        reason = self._last_failure_reason or "unknown"
        if fallback_enabled and reason in ("connectivity", "dns", "config"):
            logger.info(f"Vwarp fallback retry triggered (reason={reason}).")
            # Minimal config without test_url to avoid config parse errors
            fallback_cfg = {
                "bind": f"{bind_addr}:{port}",
                "dns": "1.1.1.1",
            }
            if await attempt("minimal-dns-only", fallback_cfg):
                return True

            # Second fallback: try alternate WARP endpoint + explicit endpoint
            # to bypass potential UDP/DNS blocks in CI environments
            logger.info(
                "Vwarp second fallback: trying alternate endpoint 162.159.193.10:1701"
            )
            fallback_cfg2 = {
                "bind": f"{bind_addr}:{port}",
                "dns": "1.0.0.1",
                "endpoint": "162.159.193.10:1701",
            }
            return await attempt("alternate-endpoint", fallback_cfg2)

        if fallback_enabled:
            logger.info(f"Vwarp fallback skipped (reason={reason}).")
        return False

    async def _start_tunnel_once(
        self,
        bind_addr: str,
        port: int,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> bool:
        self._cleanup_config_file()
        self._last_failure_reason = None
        self._last_failure_details = None
        cmd = await self._build_tunnel_command(
            bind_addr, port, config_override=config_override
        )
        if not cmd:
            logger.error("Vwarp tunnel command could not be constructed.")
            self._cleanup_config_file()
            return False
        try:
            tunnel_start = time.time()
            logger.info(
                "🚀 Starting Vwarp SOCKS5 Tunnel on %s:%d (cmd: %s)...",
                bind_addr,
                port,
                " ".join(cmd),
            )
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
                combined = (stdout or b"") + b"\n" + (stderr or b"")
                details = combined.decode(errors="ignore")
                if stdout:
                    logger.error(f"Vwarp stdout: {stdout.decode(errors='ignore')}")
                if stderr:
                    logger.error(f"Vwarp stderr: {stderr.decode(errors='ignore')}")
                if details:
                    self._record_failure(self._classify_failure(details), details)
                self._cleanup_config_file()
                return False

            # Robust port checking
            is_ready = await self._wait_for_port(bind_addr, port)
            if not is_ready:
                logger.error("Vwarp Tunnel started but port check timed out.")

                # Check for immediate exit and logs
                if self._tunnel_proc.returncode is not None:
                    stdout, stderr = await self._tunnel_proc.communicate()
                    combined = (stdout or b"") + b"\n" + (stderr or b"")
                    details = combined.decode(errors="ignore")
                    if stdout:
                        logger.debug(f"Vwarp stdout: {stdout.decode(errors='ignore')}")
                    if stderr:
                        logger.error(f"Vwarp stderr: {stderr.decode(errors='ignore')}")
                    if details and not self._last_failure_reason:
                        self._record_failure(self._classify_failure(details), details)
                else:
                    # Kill and read logs
                    try:
                        self._tunnel_proc.terminate()
                        # Allow brief time for logs to flush
                        try:
                            stdout, stderr = await safe_wait_for(
                                self._tunnel_proc.communicate(), timeout=1.0
                            )
                            combined = (stdout or b"") + b"\n" + (stderr or b"")
                            details = combined.decode(errors="ignore")
                            if stderr:
                                logger.error(
                                    f"Vwarp stderr before kill: {stderr.decode(errors='ignore')}"
                                )
                            if details and not self._last_failure_reason:
                                self._record_failure(
                                    self._classify_failure(details), details
                                )
                        except asyncio.TimeoutError:
                            self._tunnel_proc.kill()
                    except Exception as e:
                        logger.debug(f"Error killing hung vwarp: {e}")

                self._tunnel_proc = None
                if not self._last_failure_reason:
                    self._record_failure("timeout", "")
                self._cleanup_config_file()
                return False

            # Check if it died immediately after port check success (rare but possible)
            if self._tunnel_proc.returncode is not None:
                logger.error(
                    f"Vwarp tunnel exited immediately with code {self._tunnel_proc.returncode}"
                )
                self._tunnel_proc = None
                self._cleanup_config_file()
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

            elapsed = time.time() - tunnel_start
            logger.info(
                "✅ Vwarp tunnel ready on %s:%d (startup took %.1fs, pid=%s).",
                bind_addr,
                port,
                elapsed,
                self._tunnel_proc.pid,
            )
            return True
        except Exception as e:
            logger.warning(
                "Failed to start Vwarp tunnel: %s. "
                "Check config, WARP keys, and network. "
                "Use USE_VWARP_TUNNEL=false to disable.",
                e,
            )
            if self._tunnel_proc:
                try:
                    self._tunnel_proc.kill()
                except ProcessLookupError:
                    pass
                self._tunnel_proc = None
            self._cleanup_config_file()
            return False

    async def stop_tunnel(self) -> None:
        """
        Stops the background tunnel process.
        """
        if self._tunnel_proc:
            pid = self._tunnel_proc.pid
            logger.info("Stopping Vwarp tunnel (pid=%s)...", pid)
            try:
                self._tunnel_proc.terminate()
                try:
                    await safe_wait_for(self._tunnel_proc.wait(), timeout=2.0)
                    logger.info("Vwarp tunnel (pid=%s) stopped gracefully.", pid)
                except asyncio.TimeoutError:
                    self._tunnel_proc.kill()
                    logger.warning(
                        "Vwarp tunnel (pid=%s) did not stop gracefully; killed.", pid
                    )
            except ProcessLookupError:
                logger.debug("Vwarp tunnel (pid=%s) already exited.", pid)
            except Exception as e:
                logger.warning("Error stopping Vwarp tunnel (pid=%s): %s", pid, e)
            finally:
                self._tunnel_proc = None
        self._cleanup_config_file()

    def _cleanup_config_file(self) -> None:
        if self._config_owned and self._config_path:
            try:
                self._config_path.unlink(missing_ok=True)
            except Exception:  # nosec
                pass
            finally:
                self._config_path = None
                self._config_owned = False

    def _record_failure(self, reason: str, details: str) -> None:
        self._last_failure_reason = reason
        self._last_failure_details = details

    @staticmethod
    def _classify_failure(text: str) -> str:
        if not text:
            return "unknown"
        lower = text.lower()
        # Detect config parse errors specifically
        config_patterns = (
            "parse config file",
            "unknown flag",
            "invalid config",
            "unmarshal",
        )
        if any(pat in lower for pat in config_patterns):
            return "config"
        connectivity_patterns = (
            "connectivity test failed",
            "cdn-cgi/trace",
            "dial: lookup",
            "no such host",
            "temporary failure in name resolution",
            "server misbehaving",
            "i/o timeout",
            "read udp",
            "context deadline exceeded",
            "network is unreachable",
            "tls handshake timeout",
            "connection refused",
        )
        if any(pat in lower for pat in connectivity_patterns):
            if "lookup" in lower or "name resolution" in lower:
                return "dns"
            return "connectivity"
        return "other"

    def _log_config(self, label: str, config: Dict[str, Any]) -> None:
        safe = self._sanitize_config_for_log(config)
        text = json.dumps(safe, ensure_ascii=True)
        if os.environ.get("VWARP_LOG_RAW_CONFIG", "").lower() in ("1", "true", "yes"):
            logger.warning(
                "VWARP_LOG_RAW_CONFIG requested but sanitized logging is enforced."
            )
        text = SecurityValidator.sanitize_log_message(text)
        logger.info(f"Vwarp config ({label}): {text}")

    @staticmethod
    def _sanitize_config_for_log(config: Dict[str, Any]) -> Dict[str, Any]:
        redact_tokens = ("key", "token", "secret", "password", "license")

        def scrub(obj: Any) -> Any:
            if isinstance(obj, dict):
                out: Dict[str, Any] = {}
                for k, v in obj.items():
                    if any(tok in str(k).lower() for tok in redact_tokens):
                        out[k] = "[REDACTED]"
                    else:
                        out[k] = scrub(v)
                return out
            if isinstance(obj, list):
                return [scrub(i) for i in obj]
            return obj

        return scrub(dict(config))
