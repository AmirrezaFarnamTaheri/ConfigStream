# SPDX-License-Identifier: AGPL-3.0-or-later
"""
WARP Key Validation System.
Validates Cloudflare WARP private keys and account credentials.
"""

import base64
import logging
from typing import Dict, Any, Optional, Tuple
import asyncio

import httpx

logger = logging.getLogger(__name__)

# Cloudflare WARP API endpoints
API_BASE = "https://api.cloudflareclient.com/v0a2404"
from ..constants import WARP_PREFIXES


class WARPKeyValidator:
    """Validates WARP keys and account credentials."""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def validate_key_format(self, key: str) -> Tuple[bool, str]:
        """
        Validate that a key is properly formatted base64 and correct length.

        Args:
            key: Base64-encoded key string

        Returns:
            (is_valid, error_message)
        """
        if not key:
            return False, "Key is empty"

        # Check if it's valid base64
        try:
            decoded = base64.b64decode(key)
        except Exception as e:
            return False, f"Invalid base64 encoding: {e}"

        # Curve25519 keys should be 32 bytes
        if len(decoded) != 32:
            return (
                False,
                f"Invalid key length: expected 32 bytes, got {len(decoded)}",
            )

        return True, "Valid"

    def validate_reserved_bytes(self, reserved: list) -> Tuple[bool, str]:
        """
        Validate reserved bytes field.

        Args:
            reserved: List of 3 integers (0-255)

        Returns:
            (is_valid, error_message)
        """
        if not isinstance(reserved, list):
            return False, "Reserved must be a list"

        if len(reserved) != 3:
            return False, f"Reserved must have 3 elements, got {len(reserved)}"

        for i, val in enumerate(reserved):
            if not isinstance(val, int):
                return False, f"Reserved[{i}] must be an integer, got {type(val)}"
            if not 0 <= val <= 255:
                return False, f"Reserved[{i}] must be 0-255, got {val}"

        return True, "Valid"

    async def validate_account_active(self, account_id: str, token: Optional[str] = None) -> Tuple[bool, str]:
        """
        Check if a WARP account ID is active by querying Cloudflare API.

        Args:
            account_id: WARP account ID
            token: Bearer token (optional, but recommended for auth)

        Returns:
            (is_active, status_message)
        """
        if not account_id:
            return False, "Account ID is empty"

        headers = {
            "User-Agent": "okhttp/3.12.1",
            "Content-Type": "application/json; charset=UTF-8",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Try to fetch account info
                response = await client.get(
                    f"{API_BASE}/reg/{account_id}",
                    headers=headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    # Check account status
                    account_type = data.get("account", {}).get("account_type", "")
                    if account_type:
                        return True, f"Active ({account_type})"
                    return True, "Active"
                elif response.status_code == 404:
                    return False, "Account not found"
                elif response.status_code == 403:
                    return False, "Account suspended or disabled"
                else:
                    return False, f"HTTP {response.status_code}"

            except asyncio.TimeoutError:
                return False, "Timeout reaching Cloudflare API"
            except httpx.ConnectError:
                return False, "Cannot connect to Cloudflare API"
            except Exception as e:
                logger.debug(f"Account validation error: {e}")
                return False, f"Validation error: {type(e).__name__}"

    async def validate_endpoint_reachable(
        self, endpoint: str, port: int = 2408
    ) -> Tuple[bool, str]:
        """
        Check if a WARP endpoint is reachable.

        Args:
            endpoint: IP address of WARP endpoint
            port: UDP port (default 2408)

        Returns:
            (is_reachable, latency_or_error)
        """
        # UDP reachability check requires a raw socket or WireGuard handshake.
        # Here we perform static validation against known IP ranges to ensure plausibility.

        # Basic validation: Is it a valid IP?
        try:
            parts = endpoint.split(".")
            if len(parts) != 4:
                return False, "Invalid IP format"
            for part in parts:
                if not 0 <= int(part) <= 255:
                    return False, "IP octets out of range"
        except ValueError:
            return False, "Invalid IP format"

        # Check if it's in known WARP ranges
        # 162.159.192.0/24, 162.159.193.0/24, 162.159.195.0/24
        # 188.114.96.0/24, 188.114.97.0/24
        # [PHASE 19] Use centralized constant
        if any(endpoint.startswith(prefix) for prefix in WARP_PREFIXES):
            return True, "Known WARP endpoint range"

        return False, "Not a known Cloudflare WARP endpoint"

    async def validate_warp_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive validation of a WARP configuration.

        Args:
            config: Dictionary with WARP configuration fields:
                - private_key: Base64 private key
                - peer_public_key: Base64 public key
                - reserved: List of 3 bytes
                - account_id: Optional account ID
                - endpoint: Optional endpoint IP

        Returns:
            Dictionary with validation results:
                {
                    "valid": bool,
                    "errors": [str],
                    "warnings": [str],
                    "details": {...}
                }
        """
        errors = []
        warnings = []
        details = {}

        # 1. Validate private key
        private_key = config.get("private_key", "")
        valid, msg = self.validate_key_format(private_key)
        details["private_key"] = msg
        if not valid:
            errors.append(f"Private key: {msg}")

        # 2. Validate peer public key
        peer_public_key = config.get("peer_public_key", "")
        valid, msg = self.validate_key_format(peer_public_key)
        details["peer_public_key"] = msg
        if not valid:
            errors.append(f"Peer public key: {msg}")

        # 3. Validate reserved bytes
        reserved = config.get("reserved", [0, 0, 0])
        valid, msg = self.validate_reserved_bytes(reserved)
        details["reserved"] = msg
        if not valid:
            errors.append(f"Reserved bytes: {msg}")

        # 4. Validate account ID (if provided)
        account_id = config.get("account_id")
        if account_id:
            is_active, status = await self.validate_account_active(account_id)
            details["account_status"] = status
            if not is_active:
                warnings.append(f"Account validation: {status}")
        else:
            details["account_status"] = "Not provided"

        # 5. Validate endpoint (if provided)
        endpoint = config.get("endpoint")
        if endpoint:
            port = config.get("port", 2408)
            is_reachable, result = await self.validate_endpoint_reachable(
                endpoint, port
            )
            details["endpoint_reachable"] = result
            if not is_reachable:
                warnings.append(f"Endpoint validation: {result}")
        else:
            details["endpoint_reachable"] = "Not provided"

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "details": details,
        }


# Convenience function
async def validate_warp_key(
    private_key: str,
    peer_public_key: str,
    reserved: Optional[list] = None,
    account_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Quick validation of WARP credentials.

    Args:
        private_key: Base64 private key
        peer_public_key: Base64 peer public key
        reserved: Optional reserved bytes [0, 0, 0]
        account_id: Optional account ID for activation check

    Returns:
        Validation result dictionary
    """
    validator = WARPKeyValidator()
    config = {
        "private_key": private_key,
        "peer_public_key": peer_public_key,
        "reserved": reserved or [0, 0, 0],
        "account_id": account_id,
    }
    return await validator.validate_warp_config(config)
