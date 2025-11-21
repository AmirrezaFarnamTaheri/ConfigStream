from __future__ import annotations

import re
from typing import Dict, Optional

from .countries import COUNTRY_NAMES

_FLAG_PATTERN = re.compile(r"[\U0001F1E6-\U0001F1FF]{2}")
_CODE_PATTERN = re.compile(
    r"(?:"
    r"\[(?P<cc1>[A-Z]{2})\]|"
    r"\((?P<cc2>[A-Z]{2})\)|"
    r"[\-_#:](?P<cc3>[A-Z]{2})[\-_#:]|"
    r"[\-_#:](?P<cc4>[A-Z]{2})(?=$)|"
    r"(?:(?<=^)|(?<=\s))(?P<cc5>[A-Z]{2})(?=[\-_#:\s])|"
    r"::(?P<cc6>[A-Z]{2})(?:\s|$)"
    r")",
    flags=re.IGNORECASE,
)

_EXCLUDED_CODES = {
    "BY",
    "IN",
    "ON",
    "OR",
    "AS",
    "IS",
    "IT",
    "AM",
    "NO",
    "AT",
    "TO",
    "OF",
    "IF",
    "SO",
    "AN",
    "BE",
    "DO",
    "GO",
    "HE",
    "ME",
    "MY",
    "UP",
    "WE",
}


def _flag_to_country_code(flag: str) -> Optional[str]:
    if len(flag) != 2:
        return None
    code_points = [ord(char) - 0x1F1E6 + ord("A") for char in flag]
    if any(point < ord("A") or point > ord("Z") for point in code_points):
        return None
    return "".join(chr(point) for point in code_points)


def _country_payload_from_code(code: str) -> Optional[Dict[str, str]]:
    code = code.upper()
    if code not in COUNTRY_NAMES:
        return None
    return {"country_code": code, "country": COUNTRY_NAMES[code]}


def infer_country_from_remarks(remarks: str) -> Optional[Dict[str, str]]:
    if not remarks:
        return None

    flag_match = _FLAG_PATTERN.search(remarks)
    if flag_match:
        code = _flag_to_country_code(flag_match.group())
        if code:
            payload = _country_payload_from_code(code)
            if payload:
                return payload

    # Iterate through all matches to find a valid one
    # This prevents false positives (like "MY" excluded code) from blocking valid codes later in string
    for code_match in _CODE_PATTERN.finditer(remarks.upper()):
        candidate_code = (
            code_match.group("cc1")
            or code_match.group("cc2")
            or code_match.group("cc3")
            or code_match.group("cc4")
            or code_match.group("cc5")
            or code_match.group("cc6")
        )

        if not candidate_code:
            continue

        candidate_code = candidate_code.upper()

        # If it's an excluded code (common words like IS, TO, MY)
        if candidate_code in _EXCLUDED_CODES:
            full_match = code_match.group(0)
            # Only allow excluded codes if they are strongly delimited (brackets, etc.)
            if not (
                full_match.startswith("[")
                or full_match.startswith("(")
                or full_match.count("-") >= 2
                or full_match.count("_") >= 2
            ):
                continue  # Skip this match, look for next

        payload = _country_payload_from_code(candidate_code)
        if payload:
            return payload

    return None
