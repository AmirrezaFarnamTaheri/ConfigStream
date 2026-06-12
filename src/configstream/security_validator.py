# SPDX-License-Identifier: AGPL-3.0-or-later
import re
import uuid
import ipaddress

# Import urlparse directly to allow mocking in tests
from urllib.parse import urlparse
from typing import List, Tuple, TYPE_CHECKING
import logging
from .utils.bool_parser import parse_tls_flag
from .config import AppSettings

if TYPE_CHECKING:
    from configstream.models import Proxy

logger = logging.getLogger(__name__)

# Cache settings to avoid repeated pydantic_settings instantiation in per-proxy hot paths
_SETTINGS_CACHE = AppSettings()

# Pre-compiled patterns for sanitize_log_message (called per log message - extremely hot)
_LOG_UUID_RE = re.compile(
    r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
    re.IGNORECASE,
)
_LOG_USERINFO_RE = re.compile(r":([^:@]+)@")
_LOG_QUERY_SECRET_RE = re.compile(
    r"(?i)(token|access_token|api_key|apikey|license_key|key|secret|pass|password|uuid|id|auth|authorization)=([^&\s]+)"
)
_LOG_AUTH_HEADER_RE = re.compile(
    r"(?i)(authorization|auth)\s*[:=]\s*(bearer|basic)?\s*([A-Za-z0-9\-._~+/]+=*)"
)
_LOG_BEARER_RE = re.compile(r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*")
_LOG_BASE64_RE = re.compile(r"\b[A-Za-z0-9+/]{20,}={0,2}\b")
_LOG_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_LOG_IPV6_RE = re.compile(r"\b(?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}\b")
# Pre-compiled pattern for sanitize_address (called per proxy)
_SANITIZE_ADDR_RE = re.compile(r"[^a-zA-Z0-9\.\-\:\[\]]")

# Security Policies
STRICT_POLICY = {
    "allow_local_ips": False,
    "require_tls_validation": True,
    "min_credential_length": 8,
    "block_suspicious_ports": True,
}

# Permissive policy used by test suite (rejects local IPs but relaxes other checks)
TEST_POLICY = {
    "allow_local_ips": False,
    "require_tls_validation": False,
    "min_credential_length": 1,
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
        if not ip:
            return False
        ip_lower = str(ip).strip().lower()
        if ip_lower == "localhost":
            return True
        if ip_lower.endswith(".local"):
            return True
        try:
            ip_obj = ipaddress.ip_address(ip)
            return (
                ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_link_local
                or ip_obj.is_reserved
            )
        except ValueError:
            return False

    @staticmethod
    def is_valid_uuid(val: str) -> bool:
        if not val:
            return False
        try:
            uuid.UUID(str(val))
            return True
        except ValueError:
            return False

    @staticmethod
    def sanitize_log_message(msg: str, mask_patterns: bool = True) -> str:
        """Sanitizes sensitive info like UUIDs or IPs from logs."""
        if not mask_patterns:
            return msg
        # Mask UUIDs (common in VMess/VLESS configs)
        msg = _LOG_UUID_RE.sub("[UUID]", msg)
        # Mask passwords in URLs (user:pass@host)
        msg = _LOG_USERINFO_RE.sub(":[MASKED]@", msg)
        # Mask common query-style secrets (token, key, secret, password, uuid, id)
        msg = _LOG_QUERY_SECRET_RE.sub(r"\1=[MASKED]", msg)
        # Mask Authorization headers or inline auth blobs (e.g., "Authorization: Bearer ...")
        msg = _LOG_AUTH_HEADER_RE.sub(r"\1: [MASKED]", msg)
        # Mask standalone Bearer tokens
        msg = _LOG_BEARER_RE.sub("Bearer [MASKED]", msg)
        # Mask likely Base64 strings (long sequences of alphanumeric+ending with =)
        msg = _LOG_BASE64_RE.sub("[BASE64]", msg)
        # Mask IPv4 addresses
        msg = _LOG_IPV4_RE.sub("[IP]", msg)
        # Mask IPv6 addresses (best-effort)
        msg = _LOG_IPV6_RE.sub("[IP]", msg)

        return msg

    @staticmethod
    def sanitize_address(address: str) -> str:
        """
        Sanitizes an address (IP or domain) for safe output.
        Removes suspicious characters.
        """
        if not address:
            return ""
        # Basic sanitization: allow alphanumeric, dots, dashes, colons (IPv6), brackets
        return _SANITIZE_ADDR_RE.sub("", address)

    @staticmethod
    def _is_address_safe(address: str) -> bool:
        """
        Internal check for address safety. Exposed as a separate method to
        allow test-seam injection without patching the full validator.
        """
        if _SETTINGS_CACHE.ALLOW_PRIVATE_IPS:
            return True
        if SecurityValidator.is_local_ip(address):
            return False
        return True

    @staticmethod
    def validate_url(url: str) -> Tuple[bool, str]:
        """
        Basic URL validation.
        Returns (is_valid, reason).
        """
        if not url:
            return False, "empty_url"
        try:
            # Use imported urlparse
            result = urlparse(url)
            # Restrict schemes to http/https
            if result.scheme in ["http", "https"] and result.netloc:
                host = result.hostname
                if not host:
                    return False, "invalid_host"
                # Use internal check (to allow mocking by tests)
                # But careful not to crash if address is netloc
                if not SecurityValidator._is_address_safe(host):
                    return False, "unsafe_address"
                return True, "ok"
            return False, "invalid_scheme_or_netloc"
        except Exception:
            # Catch generic Exception as tests might raise arbitrary exceptions to test robustness
            return False, "parse_error"

    @staticmethod
    def validate_proxy_config(
        proxy: "Proxy", policy: dict = STRICT_POLICY
    ) -> Tuple[bool, str]:
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

        if not policy["allow_local_ips"] and SecurityValidator.is_local_ip(
            proxy.address
        ):
            return False, "local_ip_blocked"

        # Enforce TLS if required by policy
        if policy.get("require_tls_validation"):
            is_secure = False
            proto = proxy.protocol
            details = proxy.details or {}
            tls_flag = parse_tls_flag(details.get("tls"))

            if proto in ["vmess", "vless"]:
                if details.get("security") in ["tls", "reality", "auto"] or tls_flag:
                    is_secure = True
            elif proto in ("trojan", "hysteria2", "tuic", "https"):
                is_secure = True

            if not is_secure and proto not in ["wireguard"]:
                if "tls" in details and not tls_flag:
                    return False, "tls_required"

        if proxy.protocol in ["vmess", "vless"]:
            uuid_val = proxy.details.get("uuid") or getattr(proxy, "uuid", None)

            if not uuid_val:
                return False, "missing_uuid"
            if not SecurityValidator.is_valid_uuid(str(uuid_val)):
                return False, "invalid_uuid_format"

        if proxy.protocol == "trojan":
            password = proxy.details.get("password") or getattr(proxy, "uuid", None)
            if not password:
                return False, "missing_trojan_password"
            min_credential_length = int(
                policy.get(
                    "min_credential_length",
                    policy.get("min_password_length", 1),
                )
            )
            if len(str(password)) < min_credential_length:
                return False, "weak_trojan_password"

        if proxy.protocol == "shadowsocks":
            method = proxy.details.get("method", "")
            if method.lower() in ["rc4-md5", "table"]:
                return False, "insecure_encryption_method"

        return True, "ok"


def _should_include_insecure(reason: str) -> bool:
    """
    Decide whether to retain an insecure proxy for output/testing.
    Broad allowlist: retain policy rejections but keep malformed configs dropped.
    """
    if not isinstance(reason, str):
        return False
    fatal_reasons = {
        "missing_address_or_port",
        "invalid_port_range",
        "invalid_port_type",
        "missing_uuid",
        "missing_trojan_password",
    }
    return reason not in fatal_reasons


def validate_batch_configs(
    proxies: List["Proxy"], policy: dict = STRICT_POLICY
) -> List["Proxy"]:
    """
    Filters a batch of proxies, returning only the safe ones.
    """
    safe_proxies = []
    settings = AppSettings()
    include_insecure = settings.INCLUDE_INSECURE_PROXIES
    # Use SecurityValidator.validate_proxy_config to allow mocking on the class
    for p in proxies:
        is_safe, reason = SecurityValidator.validate_proxy_config(p, policy)
        if is_safe:
            p.is_secure = True
            if settings.ALLOW_PRIVATE_IPS and SecurityValidator.is_local_ip(p.address):
                p.is_secure = False
                p.security_issues.setdefault("policy", []).append("local_ip_allowed")
            safe_proxies.append(p)
        else:
            # Explicitly mark rejected proxies as insecure so tests checking them see the change
            p.is_secure = False
            if not p.security_issues:
                p.security_issues = {}
            p.security_issues.setdefault("policy", []).append(reason)

            if include_insecure and _should_include_insecure(reason):
                safe_proxies.append(p)

    return safe_proxies


def _safe_log_text(value: object) -> str:
    """Sanitize arbitrary text for logging."""
    return SecurityValidator.sanitize_log_message(str(value))


def _safe_proxy_ref(proxy: "Proxy") -> str:
    """Sanitize proxy endpoint reference for logging."""
    protocol = SecurityValidator.sanitize_log_message(
        str(getattr(proxy, "protocol", "unknown"))
    )
    return f"{protocol}://[endpoint]"


def _safe_source_ref(proxy: "Proxy") -> str:
    """Sanitize proxy source URL for logging."""
    return SecurityValidator.sanitize_log_message(
        str(getattr(proxy, "details", {}).get("_source", "unknown"))
    )
