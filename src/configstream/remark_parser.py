# src/configstream/remark_parser.py
"""
Robust, multi-stage parser for extracting location (country)
from proxy remarks (names).

This is used as a fallback when IP-based geolocation fails.
"""

import logging
import re
import functools
from typing import Dict, Set, Optional

# This relies on the existing countries.py file
try:
    from .countries import COUNTRY_NAMES
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("countries.py not found. Remark parsing will be limited.")
    COUNTRY_NAMES = {}

logger = logging.getLogger(__name__)


def _generate_country_emoji(country_code: str) -> str:
    """Generate flag emoji from 2-letter country code."""
    if not country_code or len(country_code) != 2:
        return ""
    # Convert country code to flag emoji using Unicode regional indicator symbols
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in country_code.upper())


class RemarkGeoParser:
    """
    Parses proxy names (remarks) to find a country code.

    It uses a multi-stage pipeline for highest accuracy:
    1. Check for country flag emojis (e.g., 🇺🇸)
    2. Check for standalone 2-letter ISO codes (e.g., [US])
    3. Check for full country names (e.g., United States)
    """

    def __init__(self):
        logger.debug("Initializing RemarkGeoParser...")

        # --- Pre-compile lookup maps for high performance ---

        # 1. Generate emoji map: {'🇺🇸': 'US', '🇳🇱': 'NL', ...}
        self.emoji_to_code: Dict[str, str] = {}
        for code in COUNTRY_NAMES.keys():
            if code != "XX":  # Skip "Unknown"
                emoji = _generate_country_emoji(code)
                if emoji:
                    self.emoji_to_code[emoji] = code

        # 2. ISO code set: {'US', 'NL', 'DE', ...}
        self.iso_codes_set: Set[str] = set(COUNTRY_NAMES.keys()) - {"XX"}

        # 3. Full name map: {'united states': 'US', 'netherlands': 'NL', ...}
        self.name_to_code: Dict[str, str] = {}
        for code, name in COUNTRY_NAMES.items():
            if code != "XX":  # Skip "Unknown"
                self.name_to_code[name.lower()] = code

        # --- Pre-compile Regexes ---

        # 1. Regex to find *any* country flag emoji
        if self.emoji_to_code:
            emoji_pattern = "|".join(re.escape(e) for e in self.emoji_to_code.keys())
            self.re_emoji = re.compile(emoji_pattern)
        else:
            self.re_emoji = None

        # 2. Regex to find standalone 2-letter uppercase codes.
        # \b ensures it's a "whole word" (e.g., finds 'US' but not 'USELESS')
        # Looks for codes bounded by common separators or brackets.
        self.re_iso_code = re.compile(r'[\s\[\](|_.-]([A-Z]{2})[\s\[\])|_.-]')

        # 3. Regex to clean up remark for full name search.
        # Removes common noise like protocols, latencies, numbers.
        self.re_noise = re.compile(
            r'(\b(vless|vmess|trojan|ss|ssr|hysteria2?)\b|'  # Protocols
            r'\d{1,5}\s*ms\b|'  # Latency
            r'\[.*?\]|\(.*?\)|\{.*?\}|'  # Anything in brackets
            r'[_\-|]|'  # Separators
            r'\b\d+\b)',  # Standalone numbers
            flags=re.IGNORECASE
        )

    @functools.lru_cache(maxsize=2048)  # Cache 2k lookups
    def parse(self, remark: str) -> Optional[str]:
        """
        Runs the multi-stage parsing pipeline on a single remark.

        Args:
            remark: The proxy name (e.g., "🇺🇸 [US] My Proxy 120ms")

        Returns:
            A 2-letter ISO country code (e.g., "US") or None.
        """
        if not remark:
            return None

        # --- Stage 1: Emoji Check (Highest Priority) ---
        if self.re_emoji:
            match = self.re_emoji.search(remark)
            if match:
                emoji = match.group(0)
                code = self.emoji_to_code.get(emoji)
                if code:
                    return code

        # --- Stage 2: Standalone ISO Code Check ---
        # Add spaces to help regex find codes at start/end
        padded_remark = f" {remark} "
        matches = self.re_iso_code.findall(padded_remark)
        for code in matches:
            if code in self.iso_codes_set:
                return code

        # --- Stage 3: Full Name Check (Slowest, Last Resort) ---
        if not self.name_to_code:
            return None  # No name map to check against

        # Clean the remark to make name matching easier
        cleaned_remark = self.re_noise.sub(' ', remark).lower().strip()
        if not cleaned_remark:
            return None  # Cleaning removed everything

        # Check for the longest names first for more specific matches
        # (e.g., match "United States" before "United")
        for name in sorted(self.name_to_code.keys(), key=len, reverse=True):
            # Use word boundaries for accuracy
            if re.search(r'\b' + re.escape(name) + r'\b', cleaned_remark):
                return self.name_to_code[name]

        return None
