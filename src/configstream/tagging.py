# src/configstream/tagging.py
"""
This module handles the in-place renaming (tagging) of proxy objects
based on a user-defined template.
"""

import logging
import re
from typing import List, Optional
from .models import Proxy

logger = logging.getLogger(__name__)


class FmtWrapper(dict):
    """
    A dictionary wrapper that returns an empty string "" for missing keys
    or keys whose value is None. This prevents errors during string formatting.
    """
    def __missing__(self, key: str) -> str:
        return ""


def format_proxy_name(template: str, proxy: Proxy) -> str:
    """
    Safely formats a proxy name based on a template string.

    This function is robust against missing data (like no country or latency)
    and cleans up the resulting string to avoid ugly artifacts.

    Available variables:
    - {remarks}: The original remarks/name of the proxy.
    - {protocol}: e.g., 'vless', 'trojan'
    - {country}: e.g., 'US', 'NL'
    - {country_code}: e.g., 'US', 'NL'
    - {city}: e.g., 'New York' (if available)
    - {latency}: e.g., '120'
    - {asn}: e.g., 'AS15169'
    - {address}: The proxy address (IP or domain)
    - {port}: The proxy port
    """

    # 1. Get the original name, falling back to address:port if empty/generic
    original_name = proxy.remarks
    if not original_name or original_name.lower() in ["defaultproxyname", "none", ""]:
        original_name = f"{proxy.address}:{proxy.port}"

    # 2. Create a dictionary of all possible values
    proxy_data = {
        "remarks": original_name,
        "protocol": proxy.protocol,
        "country": proxy.country_code or proxy.country,
        "country_code": proxy.country_code,
        "city": proxy.city,
        "latency": str(int(proxy.latency)) if proxy.latency is not None else None,
        "asn": proxy.asn,
        "address": proxy.address,
        "port": str(proxy.port),
    }

    try:
        # 3. Use FmtWrapper to safely substitute values.
        # This creates a dict with only non-None, non-empty values.
        safe_data = FmtWrapper({k: v for k, v in proxy_data.items() if v is not None})
        new_name = template.format_map(safe_data)

        # 4. Robust cleanup of artifacts from missing data

        # Remove empty brackets/parentheses: "[]", "()", "{}"
        new_name = re.sub(r'\[\s*\]', '', new_name)
        new_name = re.sub(r'\(\s*\)', '', new_name)
        new_name = re.sub(r'\{\s*\}', '', new_name)

        # Remove duplicate separators: " - - " -> " - "
        # This handles space, tab, hyphen, underscore, and pipe.
        new_name = re.sub(r'([ \t\-_|])\1+', r'\1', new_name)

        # Remove separators dangling at the start/end
        new_name = new_name.strip(' \t\n\r\-_|')

        # Consolidate all whitespace to a single space
        new_name = re.sub(r'\s+', ' ', new_name).strip()

        # If the name is empty after cleanup, return original name
        return new_name if new_name else original_name

    except (ValueError, KeyError) as e:
        logger.warning(
            "Could not format name template '%s' for proxy %s: %s",
            template, original_name, e
        )
        return original_name  # Return original name on any failure


class ProxyTagger:
    """
    Applies a naming template to a list of Proxy objects in-place.
    """
    def __init__(self, name_template: Optional[str] = None):
        """
        Initializes the tagger with a name template.

        Args:
            name_template: A Python format string, e.g.,
                           "[{country}] {protocol} - {latency}ms"
        """
        self.template = name_template

    def apply(self, proxies: List[Proxy]) -> List[Proxy]:
        """
        Applies renaming to a list of proxies in place.

        Returns:
            The same list of proxies, with their 'remarks' field modified.
        """
        if not self.template:
            logger.debug("No name_template provided, skipping renaming.")
            return proxies  # Do nothing if no template is set

        logger.info(
            "Applying name template '%s' to %d proxies...",
            self.template, len(proxies)
        )

        for proxy in proxies:
            # This is the key: we modify the 'remarks' field IN-PLACE
            proxy.remarks = format_proxy_name(self.template, proxy)

        return proxies
