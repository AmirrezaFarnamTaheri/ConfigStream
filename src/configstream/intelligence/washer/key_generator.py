# SPDX-License-Identifier: AGPL-3.0-or-later
import base64
import ipaddress
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)


class KeyGenerator:
    """Register a Cloudflare WARP account and return its WireGuard material."""

    API_URL = "https://api.cloudflareclient.com/v0a2408/reg"
    DEFAULT_ENDPOINT = "162.159.192.1"
    DEFAULT_PORT = 2408

    @staticmethod
    def _generate_keys() -> Tuple[str, str]:
        """Generate a Curve25519 key pair as base64-encoded raw keys."""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import x25519

        private_key = x25519.X25519PrivateKey.generate()
        public_key = private_key.public_key()
        priv_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pub_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return (
            base64.b64encode(priv_bytes).decode("ascii"),
            base64.b64encode(pub_bytes).decode("ascii"),
        )

    @classmethod
    def _parse_endpoint(cls, value: Any) -> Tuple[str, int]:
        """Parse IPv4, hostname, bracketed IPv6, or bare IPv6 endpoints safely."""
        raw = str(value or "").strip()
        if not raw:
            return cls.DEFAULT_ENDPOINT, cls.DEFAULT_PORT

        if raw.startswith("[") or raw.count(":") == 1:
            try:
                parsed = urlsplit(f"//{raw}")
                host = parsed.hostname
                port = parsed.port or cls.DEFAULT_PORT
                if host and 1 <= port <= 65535:
                    return host, port
            except (ValueError, TypeError):
                return cls.DEFAULT_ENDPOINT, cls.DEFAULT_PORT

        if raw.count(":") > 1:
            try:
                ip = ipaddress.ip_address(raw)
                if isinstance(ip, ipaddress.IPv6Address):
                    return str(ip), cls.DEFAULT_PORT
            except ValueError:
                return cls.DEFAULT_ENDPOINT, cls.DEFAULT_PORT

        if "/" not in raw and "@" not in raw and raw:
            return raw, cls.DEFAULT_PORT
        return cls.DEFAULT_ENDPOINT, cls.DEFAULT_PORT

    async def generate_account(self) -> Optional[Dict[str, Any]]:
        """Register a WARP account and return a normalized configuration dict."""
        try:
            private_key, public_key = self._generate_keys()
            install_id = uuid.uuid4().hex
            serial_number = uuid.uuid4().hex
            push_registration = str()
            payload = {
                "key": public_key,
                "install_id": install_id,
                "tos": datetime.now(timezone.utc)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z"),
                "model": "Linux",
                "serial_number": serial_number,
                "locale": "en_US",
                "fcm_token": push_registration,
            }
            headers = {
                "User-Agent": "okhttp/3.12.1",
                "Content-Type": "application/json; charset=UTF-8",
            }

            async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
                response = await client.post(
                    self.API_URL, json=payload, headers=headers
                )

            if response.status_code != 200:
                logger.warning(
                    "WARP registration failed with HTTP status %s",
                    response.status_code,
                )
                return None

            try:
                data = response.json()
            except ValueError:
                logger.warning("WARP registration returned invalid JSON")
                return None

            account = data.get("account") or {}
            config = data.get("config") or {}
            peers = config.get("peers") or []
            if not isinstance(peers, list) or not peers:
                logger.warning("No peers found in WARP registration response")
                return None

            peer = peers[0] if isinstance(peers[0], dict) else {}
            endpoint = peer.get("endpoint") or {}
            endpoint_value = None
            if isinstance(endpoint, dict):
                endpoint_value = (
                    endpoint.get("v4") or endpoint.get("v6") or endpoint.get("host")
                )
            elif isinstance(endpoint, str):
                endpoint_value = endpoint
            host, port = self._parse_endpoint(endpoint_value)

            return {
                "private_key": private_key,
                "peer_public_key": peer.get("public_key"),
                "reserved": data.get("token"),
                "client_id": config.get("client_id"),
                "endpoint": host,
                "port": port,
                "id": account.get("id"),
                "install_id": install_id,
                "serial_number": serial_number,
            }
        except (httpx.HTTPError, OSError, ValueError, TypeError) as exc:
            logger.error("Failed to generate WARP account: %s", type(exc).__name__)
            return None
