"""Enhanced security validation for proxy configurations."""

import re
import logging
from typing import Optional, List, Tuple
from urllib.parse import urlparse

from .models import Proxy
from .constants import (
    DANGEROUS_PORTS,
    SUSPICIOUS_DOMAINS,
    MAX_PORT,
    VALID_PROTOCOLS,
    MAX_CONFIG_LINE_LENGTH,
)

logger = logging.getLogger(__name__)


class SecurityValidator:
    """Validates proxy configurations for security issues."""

    @staticmethod
    def validate_proxy_config(proxy: Proxy) -> Tuple[bool, List[str]]:
        """
        Comprehensive security validation for a proxy configuration.

        Args:
            proxy: Proxy object to validate

        Returns:
            Tuple of (is_secure, list_of_issues)
        """
        issues = []

        # Port validation
        if not SecurityValidator._is_port_safe(proxy.port):
            issues.append(f"Unsafe port: {proxy.port}")

        # Address validation
        if not SecurityValidator._is_address_safe(proxy.address):
            issues.append(f"Suspicious address: {proxy.address}")

        # Protocol validation
        if not SecurityValidator._is_protocol_safe(proxy.protocol):
            issues.append(f"Unknown protocol: {proxy.protocol}")

        # Config string validation
        if not SecurityValidator._is_config_string_safe(proxy.config):
            issues.append("Config contains suspicious patterns")

        is_secure = len(issues) == 0
        return is_secure, issues

    @staticmethod
    def _is_port_safe(port: int) -> bool:
        """Check if port is in safe range."""
        if port < 1 or port > MAX_PORT:
            return False
        if port in DANGEROUS_PORTS:
            logger.warning(f"Dangerous port detected: {port}")
            return False
        return True

    @staticmethod
    def _is_address_safe(address: str) -> bool:
        """Check if address is not localhost or private IP."""
        if not address:
            return False

        address_lower = address.lower()

        # Check for suspicious patterns
        for suspicious in SUSPICIOUS_DOMAINS:
            if suspicious in address_lower:
                logger.warning(f"Suspicious address pattern: {address}")
                return False

        # Check for IPv4 private ranges (RFC 1918)
        private_ranges = [
            "10.",  # 10.0.0.0/8
            "172.16.",
            "172.17.",
            "172.18.",
            "172.19.",
            "172.20.",
            "172.21.",
            "172.22.",
            "172.23.",
            "172.24.",
            "172.25.",
            "172.26.",
            "172.27.",
            "172.28.",
            "172.29.",
            "172.30.",
            "172.31.",  # 172.16.0.0/12
            "192.168.",  # 192.168.0.0/16
        ]

        for private in private_ranges:
            if address_lower.startswith(private):
                logger.warning(f"Private IP range detected: {address}")
                return False

        # Check for link-local and special addresses
        special_addresses = [
            "169.254.",  # Link-local (APIPA)
            "127.",  # Loopback
            "0.",  # This network
            "255.255.255.255",  # Broadcast
            "::1",  # IPv6 loopback
            "fe80:",  # IPv6 link-local
            "fc00:",  # IPv6 unique local
            "fd00:",  # IPv6 unique local
        ]

        for special in special_addresses:
            if address_lower.startswith(special):
                logger.warning(f"Special address detected: {address}")
                return False

        # DNS rebinding protection - reject numeric IPs in unexpected formats
        if address_lower.startswith("0x") or address_lower.startswith("0"):
            # Hexadecimal or octal IP notation
            logger.warning(f"Non-standard IP notation: {address}")
            return False

        return True

    @staticmethod
    def _is_protocol_safe(protocol: str) -> bool:
        """Validate protocol is recognized."""
        return protocol.lower() in VALID_PROTOCOLS

    @staticmethod
    def _is_config_string_safe(config: str) -> bool:
        """Check config string for injection attempts."""
        if not config:
            return False

        # Check for null bytes
        if "\x00" in config:
            logger.error("Null byte detected in config")
            return False

        # Check for suspicious shell patterns and injection attempts
        suspicious_patterns = [
            r"\$\(",  # Command substitution
            r"`",  # Backtick command execution
            r";\s*rm\s",  # Dangerous commands
            r"&&\s*rm\s",
            r"\|\s*sh",
            r"eval\s*\(",
            r"exec\s*\(",
            r"<script",  # XSS attempts
            r"javascript:",  # JavaScript protocol
            r"data:text/html",  # Data URI XSS
            r"\bDROP\s+TABLE\b",  # SQL injection
            r"\bDELETE\s+FROM\b",
            r"\.\.\/",  # Path traversal
            r"file:\/\/",  # File protocol
            r"%00",  # Null byte in URL encoding
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, config, re.IGNORECASE):
                logger.error(f"Suspicious pattern detected: {pattern}")
                return False

        # Check length
        if len(config) > MAX_CONFIG_LINE_LENGTH:
            logger.warning(f"Config too long: {len(config)} chars")
            return False

        return True

    @staticmethod
    def validate_url(url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate URL for security issues.

        Args:
            url: URL string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url:
            return False, "Empty URL"

        try:
            parsed = urlparse(url)

            # Must have scheme
            if not parsed.scheme:
                return False, "Missing URL scheme"

            # Must be http or https
            if parsed.scheme not in ["http", "https"]:
                return False, f"Invalid scheme: {parsed.scheme}"

            # Must have netloc
            if not parsed.netloc:
                return False, "Missing domain"

            # Check for suspicious domains
            if not SecurityValidator._is_address_safe(parsed.netloc):
                return False, f"Suspicious domain: {parsed.netloc}"

            return True, None

        except Exception as e:
            return False, f"URL parsing error: {str(e)}"

    @staticmethod
    def sanitize_log_message(message: str, mask_patterns: bool = True) -> str:
        """
        Sanitize log messages to remove sensitive information.

        Args:
            message: Log message to sanitize
            mask_patterns: Whether to mask sensitive patterns

        Returns:
            Sanitized message
        """
        if not mask_patterns:
            return message

        sanitized = message

        # Mask UUIDs
        uuid_pattern = r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
        sanitized = re.sub(uuid_pattern, "[UUID]", sanitized, flags=re.IGNORECASE)

        # Mask passwords in URLs
        password_pattern = r":([^@\s]+)@"
        sanitized = re.sub(password_pattern, r":[MASKED]@", sanitized)

        # Mask base64 encoded data (if > 20 chars)
        base64_pattern = r"\b[A-Za-z0-9+/]{20,}={0,2}\b"
        sanitized = re.sub(base64_pattern, "[BASE64]", sanitized)

        return sanitized


def validate_batch_configs(proxies: List[Proxy], leniency: bool = False) -> List[Proxy]:
    """
    Validate a batch of proxy configurations and filter out insecure ones.

    Args:
        proxies: List of proxy objects
        leniency: If True, log security issues but do not filter proxies.

    Returns:
        List of secure proxy objects
    """
    validator = SecurityValidator()

    if leniency:
        logger.warning(
            "Security validation is running in leniency mode. No proxies will be filtered."
        )
        insecure_count = 0
        for proxy in proxies:
            is_secure, issues = validator.validate_proxy_config(proxy)
            if not is_secure:
                insecure_count += 1
                logger.warning(
                    f"Insecure proxy detected: {proxy.address}:{proxy.port} (issues: {', '.join(issues)})"
                )
                proxy.is_secure = False
                proxy.security_issues.extend(issues)
        logger.info(
            f"Security validation (leniency mode): Detected {insecure_count} insecure proxies, but not filtering."
        )
        return proxies

    secure_proxies = []
    for proxy in proxies:
        is_secure, issues = validator.validate_proxy_config(proxy)

        if not is_secure:
            logger.warning(f"Insecure proxy filtered: {proxy.address}:{proxy.port}")
            logger.debug(f"Security issues: {', '.join(issues)}")
            proxy.is_secure = False
            proxy.security_issues.extend(issues)
        else:
            secure_proxies.append(proxy)

    logger.info(f"Security validation: {len(secure_proxies)}/{len(proxies)} proxies passed")

    return secure_proxies
