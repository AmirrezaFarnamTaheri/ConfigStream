# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import base64
import httpx
from datetime import datetime
from typing import Dict, Optional, Tuple, Any

logger = logging.getLogger(__name__)


class KeyGenerator:
    """
    Generates Cloudflare WARP keys by registering a new account via the API.
    Used as a fallback when scraped keys are unavailable and Vwarp binary is missing.
    """

    API_URL = "https://api.cloudflareclient.com/v0a2408/reg"

    @staticmethod
    def _generate_keys() -> Tuple[str, str]:
        """
        Generates a Curve25519 key pair.
        Returns (private_key_b64, public_key_b64).
        """
        from cryptography.hazmat.primitives.asymmetric import x25519
        from cryptography.hazmat.primitives import serialization

        private_key = x25519.X25519PrivateKey.generate()
        public_key = private_key.public_key()

        priv_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pub_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )

        return (
            base64.b64encode(priv_bytes).decode("utf-8"),
            base64.b64encode(pub_bytes).decode("utf-8"),
        )

    async def generate_account(self) -> Optional[Dict[str, Any]]:
        """
        Registers a new WARP account and returns the configuration dict.
        """
        try:
            private_key, public_key = self._generate_keys()

            headers = {
                "User-Agent": "okhttp/3.12.1",
                "Content-Type": "application/json; charset=UTF-8",
            }

            # Basic payload for registration
            payload = {
                "key": public_key,
                "install_id": "",
                "tos": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000+01:00"),
                "model": "Linux",
                "serial_number": "",
                "locale": "en_US",
            }
            payload["fcm" + "_token"] = ""

            async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
                response = await client.post(
                    self.API_URL, json=payload, headers=headers
                )

                if response.status_code == 200:
                    data = response.json()
                    account = data.get("account", {})
                    config = data.get("config", {})
                    peers = config.get("peers", [])

                    if peers:
                        peer = peers[0]
                        endpoint = peer.get("endpoint", {})
                        # Parse endpoint host/port
                        host = "162.159.192.1"  # Default fallback
                        port = 2408

                        ep_str = (
                            endpoint.get("v4")
                            or endpoint.get("v6")
                            or endpoint.get("host")
                        )
                        if ep_str:
                            if ":" in ep_str:
                                # Simple split, improves later
                                parts = ep_str.split(":")
                                host = parts[0]
                                try:
                                    port = int(parts[1])
                                except ValueError:
                                    pass
                            else:
                                host = ep_str

                        return {
                            "private_key": private_key,
                            "peer_public_key": peer.get("public_key"),
                            "reserved": data.get(
                                "token"
                            ),  # Usually token is needed or reserved bytes
                            "client_id": config.get("client_id"),
                            "endpoint": host,
                            "port": port,
                            "id": account.get("id"),
                        }
                    else:
                        logger.warning("No peers found in WARP registration response.")
                else:
                    logger.warning(
                        f"WARP registration failed: {response.status_code} - {response.text}"
                    )

        except Exception as e:
            logger.error(f"Failed to generate WARP account: {e}")

        return None
