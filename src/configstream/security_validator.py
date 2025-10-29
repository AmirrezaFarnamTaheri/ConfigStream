"""Enhanced security validation for proxy configurations."""

import re
import logging
from dataclasses import dataclass, replace
from typing import Optional, List, Tuple, Dict, FrozenSet
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


# RFC 2606 reserved names + localhost: safe for tests and docs
RESERVED_DOMAINS: FrozenSet[str] = frozenset(
    {
        "example.com",
        "example.org",
        "example.net",
        "localhost",
        "invalid",  # TLD "test" is a suffix, handle via endswith(".test")
    }
)


@dataclass(frozen=True)
class ValidationPolicy:
    check_suspicious_domains: bool = True
    check_ports: bool = True
    check_protocols: bool = True
    check_config_string: bool = True
    # allowlist domains that should never be flagged as “suspicious”
    suspicious_domain_allowlist: FrozenSet[str] = RESERVED_DOMAINS


STRICT_POLICY = ValidationPolicy()
TEST_POLICY = replace(
    STRICT_POLICY,
    # Keep checks but allow specific fixtures like "example.com"
    suspicious_domain_allowlist=STRICT_POLICY.suspicious_domain_allowlist
    | frozenset({"valid-proxy-domain.com", "another-valid-proxy.net"}),
)


# Security issue categories for better classification
SECURITY_CATEGORIES = {
    "PORT_UNSAFE": "port_security",
    "ADDRESS_PRIVATE": "address_private_ip",
    "ADDRESS_SUSPICIOUS": "address_suspicious",
    "PROTOCOL_UNKNOWN": "protocol_invalid",
    "INJECTION_RISK": "suspicious_injection_attempt",
    "CONFIG_TOO_LONG": "suspicious_config_format",
    "CONFIG_NULL_BYTE": "suspicious_config_malformed",
}


class SecurityValidator:
    """Validates proxy configurations for security issues with detailed categorization."""

    @staticmethod
    def validate_proxy_config(
        proxy: Proxy, policy: ValidationPolicy = STRICT_POLICY
    ) -> Tuple[bool, Dict[str, List[str]]]:
        """
        Comprehensive security validation for a proxy configuration.

        Args:
            proxy: Proxy object to validate
            policy: The validation policy to apply.

        Returns:
            Tuple of (is_secure, categorized_issues_dict)
        """
        categorized_issues: Dict[str, List[str]] = {}

        # Port validation
        if policy.check_ports:
            port_issue = SecurityValidator._validate_port(proxy.port)
            if port_issue:
                category = SECURITY_CATEGORIES["PORT_UNSAFE"]
                if category not in categorized_issues:
                    categorized_issues[category] = []
                categorized_issues[category].append(port_issue)

        # Address validation
        if policy.check_suspicious_domains:
            address_issues = SecurityValidator._validate_address(
                proxy.address, policy.suspicious_domain_allowlist
            )
            for category, issue in address_issues.items():
                if category not in categorized_issues:
                    categorized_issues[category] = []
                categorized_issues[category].append(issue)

        # Protocol validation
        if policy.check_protocols:
            protocol_issue = SecurityValidator._validate_protocol(proxy.protocol)
            if protocol_issue:
                category = SECURITY_CATEGORIES["PROTOCOL_UNKNOWN"]
                if category not in categorized_issues:
                    categorized_issues[category] = []
                categorized_issues[category].append(protocol_issue)

        # Config string validation
        if policy.check_config_string:
            config_issues = SecurityValidator._validate_config_string(proxy.config)
            for category, issue in config_issues.items():
                if category not in categorized_issues:
                    categorized_issues[category] = []
                categorized_issues[category].append(issue)

        is_secure = len(categorized_issues) == 0
        return is_secure, categorized_issues

    @staticmethod
    def _validate_port(port: int) -> Optional[str]:
        """Check if port is safe and return issue if not."""
        if port < 1 or port > MAX_PORT:
            return f"Port out of valid range (1-{MAX_PORT}): {port}"
        if port in DANGEROUS_PORTS:
            logger.warning(f"Dangerous port detected: {port}")
            return f"Dangerous port: {port}"
        return None

    @staticmethod
    def _validate_address(
        address: str, suspicious_domain_allowlist: FrozenSet[str]
    ) -> Dict[str, str]:
        """Check address safety and return categorized issues."""
        issues = {}

        if not address:
            issues[SECURITY_CATEGORIES["ADDRESS_SUSPICIOUS"]] = "Empty address"
            return issues

        address_lower = address.lower()

        # Allow bypass for reserved or test-specific domains
        if address_lower in suspicious_domain_allowlist or address_lower.endswith(".test"):
            pass
        # Check for suspicious patterns (exact or subdomain match)
        for suspicious in SUSPICIOUS_DOMAINS:
            if address_lower == suspicious or address_lower.endswith("." + suspicious):
                logger.warning(f"Suspicious address pattern found: {address}")
                issues[SECURITY_CATEGORIES["ADDRESS_SUSPICIOUS"]] = (
                    f"Suspicious address pattern: {address}"
                )
                return issues

        # DNS rebinding protection - check for hex notation or octal notation
        if address_lower.startswith("0x") or re.match(r"^0[0-7]{1,11}\.", address_lower):
            logger.warning(f"Non-standard IP notation: {address}")
            issues[SECURITY_CATEGORIES["ADDRESS_SUSPICIOUS"]] = f"Non-standard notation: {address}"
            return issues

        # Combined check for private, reserved, and special-use addresses
        # This is more robust and covers more edge cases.
        special_address_patterns = [
            # Loopback
            r"^127\.",
            r"^::1$",
            r"^localhost$",
            # Private ranges
            r"^10\.",
            r"^172\.(1[6-9]|2[0-9]|3[0-1])\.",
            r"^192\.168\.",
            # Link-local
            r"^169\.254\.",
            r"^fe80:",
            # Unique local
            r"^fc00:",
            r"^fd00:",
            # Unspecified
            r"^0\.0\.0\.0$",
            r"^0\.",  # "This network"
            # Broadcast
            r"^255\.255\.255\.255$",
        ]

        for pattern in special_address_patterns:
            if re.match(pattern, address_lower):
                logger.warning(f"Special or private address detected: {address}")
                issues[SECURITY_CATEGORIES["ADDRESS_PRIVATE"]] = f"Special address: {address}"
                return issues

        return issues

    @staticmethod
    def _validate_protocol(protocol: str) -> Optional[str]:
        """Validate protocol is recognized."""
        if protocol.lower() not in VALID_PROTOCOLS:
            return f"Unknown protocol: {protocol}"
        return None

    @staticmethod
    def _validate_config_string(config: str) -> Dict[str, str]:
        """Check config string for injection attempts and return categorized issues."""
        issues = {}

        if not config:
            issues[SECURITY_CATEGORIES["CONFIG_TOO_LONG"]] = "Suspicious: Empty config"
            return issues

        # Check for null bytes
        if "\x00" in config:
            logger.error("Null byte detected in config")
            issues[SECURITY_CATEGORIES["CONFIG_NULL_BYTE"]] = "Suspicious: Contains null byte"
            return issues

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
                issues[SECURITY_CATEGORIES["INJECTION_RISK"]] = (
                    "Suspicious: Potential injection pattern detected"
                )
                return issues

        # Check length
        if len(config) > MAX_CONFIG_LINE_LENGTH:
            logger.warning(f"Config too long: {len(config)} chars")
            issues[SECURITY_CATEGORIES["CONFIG_TOO_LONG"]] = (
                f"Config exceeds max length: {len(config)} chars"
            )
            return issues

        return issues

    # Backward compatibility methods
    @staticmethod
    def _is_port_safe(port: int) -> bool:
        """Backward compatibility: Check if port is in safe range."""
        return SecurityValidator._validate_port(port) is None

    @staticmethod
    def _is_address_safe(address: str) -> bool:
        """Backward compatibility: Check if address is safe."""
        # Note: Uses an empty allowlist for the strictest check.
        return len(SecurityValidator._validate_address(address, frozenset())) == 0

    @staticmethod
    def _is_protocol_safe(protocol: str) -> bool:
        """Backward compatibility: Validate protocol is recognized."""
        return SecurityValidator._validate_protocol(protocol) is None

    @staticmethod
    def _is_config_string_safe(config: str) -> bool:
        """Backward compatibility: Check config string for injection attempts."""
        return len(SecurityValidator._validate_config_string(config)) == 0

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


def validate_batch_configs(
    proxies: List[Proxy], policy: ValidationPolicy = STRICT_POLICY
) -> List[Proxy]:
    """
    Validate a batch of proxy configurations and filter out insecure ones.

    Args:
        proxies: List of proxy objects
        policy: The validation policy to apply.

    Returns:
        List of secure proxy objects
    """
    validator = SecurityValidator()
    secure_proxies = []

    for proxy in proxies:
        is_secure, categorized_issues = validator.validate_proxy_config(proxy, policy=policy)

        if not is_secure:
            all_issues = []
            for category, issues_list in categorized_issues.items():
                all_issues.extend(issues_list)

            logger.warning(f"Insecure proxy filtered: {proxy.address}:{proxy.port}")
            logger.debug(f"Security issues: {', '.join(all_issues)}")
            proxy.is_secure = False
            proxy.security_issues = categorized_issues
        else:
            proxy.is_secure = True
            secure_proxies.append(proxy)

    logger.info(f"Security validation: {len(secure_proxies)}/{len(proxies)} proxies passed")
    return secure_proxies
