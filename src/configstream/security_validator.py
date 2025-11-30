"""Enhanced security validation for proxy configurations."""

import re
import uuid
import json
import logging
from dataclasses import dataclass, replace
from typing import List, Tuple, Dict, FrozenSet, Optional
from urllib.parse import urlparse

from .models import Proxy
from .security.blocklist import DEFAULT_BLOCKLIST
from .security.rules import (
    SECURITY_CATEGORIES,
    validate_port,
    validate_address,
    validate_protocol,
    validate_config_string,
)

logger = logging.getLogger(__name__)

# RFC 2606 reserved names + localhost: safe for tests and docs
RESERVED_DOMAINS: FrozenSet[str] = frozenset(
    {
        "example.com",
        "example.org",
        "example.net",
        "localhost",
        "invalid",
    }
)


@dataclass(frozen=True)
class ValidationPolicy:
    check_suspicious_domains: bool = True
    check_ports: bool = True
    check_protocols: bool = True
    check_config_string: bool = True
    check_blocklist: bool = True
    # allowlist domains that should never be flagged as “suspicious”
    suspicious_domain_allowlist: FrozenSet[str] = RESERVED_DOMAINS


STRICT_POLICY = ValidationPolicy()
TEST_POLICY = replace(
    STRICT_POLICY,
    suspicious_domain_allowlist=STRICT_POLICY.suspicious_domain_allowlist
    | frozenset({"valid-proxy-domain.com", "another-valid-proxy.net"}),
)


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
            port_issue = validate_port(proxy.port)
            if port_issue:
                category = SECURITY_CATEGORIES["PORT_UNSAFE"]
                if category not in categorized_issues:
                    categorized_issues[category] = []
                categorized_issues[category].append(port_issue)

            # Honeypot Check (Static Port Check)
            if DEFAULT_BLOCKLIST.is_honeypot(proxy.address, proxy.port):
                category = SECURITY_CATEGORIES["HONEYPOT_SUSPECTED"]
                if category not in categorized_issues:
                    categorized_issues[category] = []
                categorized_issues[category].append(
                    "Potentially malicious honeypot port"
                )

        # Address validation
        if policy.check_suspicious_domains:
            address_issues = validate_address(
                proxy.address, policy.suspicious_domain_allowlist
            )
            for category, issue in address_issues.items():
                if category not in categorized_issues:
                    categorized_issues[category] = []
                categorized_issues[category].append(issue)

        # Blocklist Validation
        if policy.check_blocklist:
            if DEFAULT_BLOCKLIST.is_blocked(proxy.address):
                category = SECURITY_CATEGORIES["ADDRESS_BLOCKED"]
                if category not in categorized_issues:
                    categorized_issues[category] = []
                categorized_issues[category].append(
                    f"Address {proxy.address} is in FireHol Level 1 blocklist"
                )

        # Protocol validation
        if policy.check_protocols:
            protocol_issue = validate_protocol(proxy.protocol)
            if protocol_issue:
                category = SECURITY_CATEGORIES["PROTOCOL_UNKNOWN"]
                if category not in categorized_issues:
                    categorized_issues[category] = []
                categorized_issues[category].append(protocol_issue)

        # Config string validation
        if policy.check_config_string:
            config_issues = validate_config_string(proxy.config)
            for category, issue in config_issues.items():
                if category not in categorized_issues:
                    categorized_issues[category] = []
                categorized_issues[category].append(issue)

        # UUID format validation for UUID-based protocols
        # Only validate UUID for protocols that strictly require it (VMess, VLESS).
        # Protocols like Trojan use passwords (any string) which are stored in proxy.uuid.
        if proxy.uuid and proxy.protocol in ("vmess", "vless"):
            try:
                # Raises ValueError for invalid UUID formats
                uuid.UUID(str(proxy.uuid))
            except (ValueError, AttributeError, TypeError):
                category = SECURITY_CATEGORIES["UUID_INVALID"]
                if category not in categorized_issues:
                    categorized_issues[category] = []
                categorized_issues[category].append(
                    f"Invalid UUID format: {proxy.uuid!r}"
                )

        is_secure = len(categorized_issues) == 0

        # Log granular rejection details for debugging
        if not is_secure and logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Validation failed for {proxy.address}:{proxy.port} (Proto: {proxy.protocol}): "
                f"{json.dumps(categorized_issues)}"
            )

        return is_secure, categorized_issues

    # Wrapper methods for internal/backward compatibility
    @staticmethod
    def _validate_port(port: int) -> Optional[str]:
        return validate_port(port)

    @staticmethod
    def _validate_address(
        address: str, suspicious_domain_allowlist: FrozenSet[str]
    ) -> Dict[str, str]:
        return validate_address(address, suspicious_domain_allowlist)

    @staticmethod
    def _validate_protocol(protocol: str) -> Optional[str]:
        return validate_protocol(protocol)

    @staticmethod
    def _validate_config_string(config: str) -> Dict[str, str]:
        return validate_config_string(config)

    # Backward compatibility methods
    @staticmethod
    def _is_port_safe(port: int) -> bool:
        """Backward compatibility: Check if port is in safe range."""
        return validate_port(port) is None

    @staticmethod
    def _is_address_safe(address: str) -> bool:
        """Backward compatibility: Check if address is safe."""
        # Note: Uses an empty allowlist for the strictest check.
        return len(validate_address(address, frozenset())) == 0

    @staticmethod
    def _is_protocol_safe(protocol: str) -> bool:
        """Backward compatibility: Validate protocol is recognized."""
        return validate_protocol(protocol) is None

    @staticmethod
    def _is_config_string_safe(config: str) -> bool:
        """Backward compatibility: Check config string for injection attempts."""
        return len(validate_config_string(config)) == 0

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
            # Use hostname to exclude port number from validation
            hostname = parsed.hostname or parsed.netloc
            if not SecurityValidator._is_address_safe(hostname):
                return False, f"Suspicious domain: {hostname}"

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
        uuid_pattern = (
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
        )
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
    rejection_reasons: Dict[str, int] = {}

    for proxy in proxies:
        is_secure, categorized_issues = validator.validate_proxy_config(
            proxy, policy=policy
        )

        if not is_secure:
            all_issues = []
            for category, issues_list in categorized_issues.items():
                all_issues.extend(issues_list)
                rejection_reasons[category] = rejection_reasons.get(category, 0) + 1

            # Only log at debug level to avoid spam, summarize at end
            logger.debug(
                f"Insecure proxy filtered: {proxy.address}:{proxy.port} - {', '.join(all_issues)}"
            )
            proxy.is_secure = False
            proxy.security_issues = categorized_issues
        else:
            proxy.is_secure = True
            secure_proxies.append(proxy)

    # Log summary instead of individual warnings
    rejected_count = len(proxies) - len(secure_proxies)
    if rejected_count > 0:
        logger.info(
            f"Security validation: {len(secure_proxies)}/{len(proxies)} proxies passed "
            f"({rejected_count} filtered). Reasons: {json.dumps(rejection_reasons)}"
        )
    else:
        logger.info(
            f"Security validation: {len(secure_proxies)}/{len(proxies)} proxies passed"
        )
    return secure_proxies
