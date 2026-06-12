# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Cloudflare WARP Account Generator.
Registers a new device with Cloudflare and generates a WireGuard proxy config.

Key generation is delegated to the canonical KeyGenerator in
``intelligence.washer.key_generator`` to avoid duplication.
"""

import logging
import datetime
import asyncio
from secrets import choice as secure_choice
from typing import Optional, Dict, Any

import httpx
from ..models import Proxy
from ..intelligence.washer.key_generator import KeyGenerator

logger = logging.getLogger(__name__)

API_BASE = "https://api.cloudflareclient.com/v0a2404"
HEADERS = {
    "User-Agent": "okhttp/3.12.1",
    "Content-Type": "application/json; charset=UTF-8",
}


async def register_warp_account() -> Optional[Dict[str, Any]]:
    """
    Register a new WARP account and return credentials.
    """
    client = httpx.AsyncClient(headers=HEADERS, timeout=15.0)

    try:
        # 1. Generate Instance ID
        inst_id = "".join(secure_choice("0123456789ABCDEF") for _ in range(22))

        # 2. Generate Keys (delegated to canonical KeyGenerator)
        try:
            loop = asyncio.get_running_loop()
            private_key, public_key = await loop.run_in_executor(
                None, KeyGenerator._generate_keys
            )
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

        # Safely extract peer data (list index out of range protection)
        peers = data.get("config", {}).get("peers", [])
        peer_data = peers[0] if peers else {}
        endpoint_v4 = peer_data.get("endpoint", {}).get("v4", {})
        interface_addresses = (
            data.get("config", {}).get("interface", {}).get("addresses", {})
        )

        return {
            "id": data.get("id"),
            "private_key": private_key,
            "peer_public_key": peer_data.get("public_key"),
            "reserved": endpoint_v4.get("reserved"),
            "address": interface_addresses.get("v4"),
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
