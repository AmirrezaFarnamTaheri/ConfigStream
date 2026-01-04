# SPDX-License-Identifier: AGPL-3.0-or-later
import re
import uuid
import binascii
from typing import List, Optional, Tuple, TYPE_CHECKING
from pydantic import ValidationError
import logging

if TYPE_CHECKING:
    from configstream.models import Proxy

logger = logging.getLogger(__name__)

# Security Policies
STRICT_POLICY = {
    "allow_local_ips": False,
    "require_tls_validation": True,
    "min_password_length": 8,
    "block_suspicious_ports": True,
}

TEST_POLICY = {
    "allow_local_ips": True,  # Allow for testing local setups
    "require_tls_validation": False,
    "min_password_length": 1,
    "block_suspicious_ports": False,
}

# Suspicious ports (commonly used for amplification attacks or malware)
SUSPICIOUS_PORTS = {
    21,
    22,
    23,
    25,
    53,
    135,
    137,
    138,
    139,
    445,
    3389,
    5900,
    11211,  # Memcached
    6379,  # Redis
}

# Local IP ranges (IPv4)
LOCAL_IP_RANGES = [
    re.compile(r"^127\."),
    re.compile(r"^10\."),
    re.compile(r"^172\.(1[6-9]|2[0-9]|3[0-1])\."),
    re.compile(r"^192\.168\."),
    re.compile(r"^169\.254\."),
]


class SecurityValidator:
    @staticmethod
    def is_local_ip(ip: str) -> bool:
        for pattern in LOCAL_IP_RANGES:
            if pattern.match(ip):
                return True
        return False

    @staticmethod
    def is_valid_uuid(val: str) -> bool:
        if not val:
            return False
        # [FIX] Relax UUID check: allow shorter strings as "password" for VLESS/VMESS
        if len(val) < 8:
             return bool(re.match(r'^[a-zA-Z0-9_\-]+$', val))
        try:
            uuid.UUID(val)
            return True
        except ValueError:
            return bool(re.match(r'^[a-zA-Z0-9_\-]+$', val))

    @staticmethod
    def is_hex(val: str) -> bool:
        try:
            int(val, 16)
            return True
        except ValueError:
            return False

    @staticmethod
    def sanitize_log_message(msg: str) -> str:
        """Sanitizes sensitive info like UUIDs or IPs from logs."""
        msg = re.sub(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '********-****-****-****-************', msg, flags=re.IGNORECASE)
        return msg


def validate_proxy(proxy: "Proxy", policy: dict = STRICT_POLICY) -> Tuple[bool, str]:
    """
    Validates a proxy configuration against a security policy.
    Returns (is_safe, rejection_reason).
    """
    if not proxy.address or not proxy.port:
        return False, "missing_address_or_port"

    try:
        port = int(proxy.port)
        if not (0 < port < 65536):
            return False, "invalid_port_range"
    except ValueError:
        return False, "invalid_port_type"

    if policy["block_suspicious_ports"] and port in SUSPICIOUS_PORTS:
        return False, f"suspicious_port_{port}"

    if not policy["allow_local_ips"] and SecurityValidator.is_local_ip(proxy.address):
        return False, "local_ip_blocked"

    if proxy.protocol in ["vmess", "vless"]:
        uuid_val = proxy.details.get("uuid")
        if not uuid_val or not SecurityValidator.is_valid_uuid(uuid_val):
             if not uuid_val:
                 return False, "missing_uuid"
             if not SecurityValidator.is_valid_uuid(uuid_val):
                  return False, "invalid_uuid_format"

    if proxy.protocol == "trojan":
        password = proxy.details.get("password")
        if not password or len(password) < policy["min_password_length"]:
            return False, "weak_trojan_password"

    if proxy.protocol == "shadowsocks":
        method = proxy.details.get("method", "")
        if method.lower() in ["rc4-md5", "table"]:
            return False, "insecure_encryption_method"

    return True, "ok"

# [BACKWARD COMPATIBILITY]
def validate_proxy_config(proxy: "Proxy", policy: dict = STRICT_POLICY) -> Tuple[bool, str]:
    """Alias for validate_proxy to maintain backward compatibility."""
    return validate_proxy(proxy, policy)


def validate_batch_configs(
    proxies: List["Proxy"], policy: dict = STRICT_POLICY
) -> List["Proxy"]:
    """
    Filters a batch of proxies, returning only the safe ones.
    """
    safe_proxies = []
    for p in proxies:
        is_safe, reason = validate_proxy(p, policy)
        if is_safe:
            safe_proxies.append(p)
    return safe_proxies
