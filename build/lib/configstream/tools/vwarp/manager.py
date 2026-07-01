# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from configstream.constants import VWARP_SOCKS5_PORT, VWARP_BIND_ADDRESS
from .binary import ensure_installed, verify_binary
from .config import build_vwarp_config, generate_masque_config
from .scanner import scan_endpoints
from .tunnel import VwarpTunnel

logger = logging.getLogger(__name__)


class VwarpTool:
    """
    High-level controller for the Vwarp utility.
    Orchestrates installation, scanning, configuration, and tunneling.
    """

    def __init__(self) -> None:
        self.binary_path: Optional[str] = None
        self.tunnel = VwarpTunnel(None)

    async def _ensure_binary(self) -> bool:
        if self.binary_path and await verify_binary(self.binary_path):
            return True
        self.binary_path = await ensure_installed()
        if self.binary_path:
            self.tunnel.binary_path = self.binary_path
            return True
        return False

    async def is_available(self) -> bool:
        """Checks if Vwarp binary is available."""
        return await self._ensure_binary()

    async def scan_endpoints(self, rtt_limit: str = "800ms") -> List[Tuple[str, int]]:
        """Scans for healthy endpoints."""
        if not await self._ensure_binary():
            return []
        return await scan_endpoints(self.binary_path, rtt_limit=rtt_limit)

    async def start_tunnel(
        self,
        bind_addr: str = VWARP_BIND_ADDRESS,
        port: int = VWARP_SOCKS5_PORT,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Starts the Vwarp SOCKS5 tunnel."""
        if not await self._ensure_binary():
            return False
        return await self.tunnel.start(bind_addr, port, config_override)

    async def stop_tunnel(self) -> None:
        """Stops the Vwarp SOCKS5 tunnel."""
        await self.tunnel.stop()

    @staticmethod
    def build_config(
        bind: str = "127.0.0.1:8086",
        endpoint: str = "162.159.192.1:2408",
        key: Optional[str] = None,
        dns: str = "1.1.1.1",
        masque_preset: Optional[str] = None,
        atomicnoize_preset: Optional[str] = None,
        psiphon_country: Optional[str] = None,
        proxy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Builds configuration."""
        return build_vwarp_config(
            bind=bind,
            endpoint=endpoint,
            key=key,
            dns=dns,
            masque_preset=masque_preset,
            atomicnoize_preset=atomicnoize_preset,
            psiphon_country=psiphon_country,
            proxy=proxy,
        )

    build_vwarp_config = build_config

    @staticmethod
    def _write_temp_config(config: Dict[str, Any]) -> Tuple[Optional[Path], List[str]]:
        from .config import write_temp_config

        return write_temp_config(config)

    @staticmethod
    def validate_warp_key(key: str) -> bool:
        """Validates a WARP key structure."""
        if not key:
            return False
        import re

        if not re.match(r"^[a-zA-Z0-9+/=_-]{40,}$", key):
            logger.warning("Invalid WARP key format")
            return False
        return True

    @staticmethod
    def build_masque_config(preset: str = "gfw") -> Dict[str, Any]:
        """Builds MASQUE configuration."""
        return generate_masque_config(preset=preset)
