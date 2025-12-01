"""
Cloudflare WARP Account Generator.
Registers a new device with Cloudflare and generates a WireGuard proxy config.
"""

import logging
import random
import datetime
from typing import Optional, Dict, Any
import base64

import httpx
from ..models import Proxy

# Import cryptography for key generation
try:
    from cryptography.hazmat.primitives.asymmetric import x25519
    from cryptography.hazmat.primitives import serialization

    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

logger = logging.getLogger(__name__)

API_BASE = "https://api.cloudflareclient.com/v0a2404"
HEADERS = {
    "User-Agent": "okhttp/3.12.1",
    "Content-Type": "application/json; charset=UTF-8",
}


def _generate_keys() -> tuple[str, str]:
    """
    Generate Curve25519 private and public keys.
    Returns (private_key_b64, public_key_b64).
    """
    if not HAS_CRYPTO:
        raise ImportError("cryptography package is required for WARP key generation")

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


async def register_warp_account() -> Optional[Dict[str, Any]]:
    """
    Register a new WARP account and return credentials.
    """
    client = httpx.AsyncClient(headers=HEADERS, timeout=15.0)

    try:
        # 1. Generate Instance ID
        inst_id = "".join(random.choices("0123456789ABCDEF", k=22))

        # 2. Generate Keys
        try:
            private_key, public_key = _generate_keys()
        except ImportError:
            logger.error("Cannot generate WARP keys: cryptography module missing")
            return None

        payload = {
            "install_id": inst_id,
            "tos": str(datetime.datetime.now().isoformat() + "+08:00"),
            "key": public_key,
            "fcm_token": f"{inst_id}:device_token",
            "type": "Android",
            "locale": "en_US",
        }

        # 3. Register
        response = await client.post(f"{API_BASE}/reg", json=payload)
        if response.status_code != 200:
            logger.error(f"WARP registration failed: {response.text}")
            return None

        data = response.json()

        return {
            "id": data.get("id"),
            "private_key": private_key,
            "peer_public_key": (
                data.get("config", {}).get("peers", [])[0].get("public_key")
                if data.get("config", {}).get("peers")
                else None
            ),
            "reserved": (
                data.get("config", {})
                .get("peers", [])[0]
                .get("endpoint", {})
                .get("v4", {})
                .get("reserved")
                if data.get("config", {}).get("peers")
                else None
            ),
            "address": data.get("config", {})
            .get("interface", {})
            .get("addresses", {})
            .get("v4"),
        }

    except Exception as e:
        logger.error(f"WARP registration failed: {e}")
        return None
    finally:
        await client.aclose()


async def generate_warp_proxy() -> Proxy:
    """
    Generate a ready-to-use Proxy object for WARP.
    """
    account = await register_warp_account()

    if not account:
        # Fallback if registration fails (should handle gracefully)
        return Proxy(
            config="warp://auto",
            protocol="wireguard",
            address="162.159.192.1",
            port=2408,
            uuid="WARP-Error",
            remarks="⚠️ Cloudflare WARP (Registration Failed)",
            country_code="US",
            is_working=False,
        )

    return Proxy(
        config="warp://auto",
        protocol="wireguard",
        address="162.159.192.1",
        port=2408,
        uuid=f"WARP-{account['id'][:8]}",
        remarks="☁️ Cloudflare WARP",
        country_code="US",
        details={
            "private_key": account["private_key"],
            "peer_public_key": account["peer_public_key"]
            or "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
            "reserved": account["reserved"] or [0, 0, 0],
            "mtu": 1280,
            "local_address": account.get("address"),
        },
        is_working=True,
    )
