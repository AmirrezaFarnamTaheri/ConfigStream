# SPDX-License-Identifier: AGPL-3.0-or-later
from configstream.country_inferrer import (
    infer_country_from_remarks,
    _flag_to_country_code,
    _country_payload_from_code,
)


def test_infer_from_name():
    res = infer_country_from_remarks("My Server (US)")
    assert res is not None
    assert res["country_code"] == "US"

    res = infer_country_from_remarks("Server [DE]")
    assert res["country_code"] == "DE"

    res = infer_country_from_remarks("Nothing here")
    assert res is None


def test_infer_priority():
    # If explicit code is present, it should take precedence?
    # Actually the current logic finds ALL codes and picks the first valid one not excluded.
    res = infer_country_from_remarks("Server (US) [DE]")
    # It depends on regex order.
    assert res is not None
    assert res["country_code"] in ["US", "DE"]


def test_infer_case_insensitive():
    res = infer_country_from_remarks("usa server (us)")
    assert res["country_code"] == "US"


def test_flag_conversion():
    assert _flag_to_country_code("🇺🇸") == "US"
    assert _flag_to_country_code("🇩🇪") == "DE"
    assert _flag_to_country_code("🏳️") is None
    assert _flag_to_country_code("Nothing") is None


def test_payload_generation():
    payload = _country_payload_from_code("US")
    assert payload["country_code"] == "US"
    assert payload["country"] == "United States"


def test_infer_from_flag_in_remarks():
    res = infer_country_from_remarks("Server 🇺🇸 Fast")
    assert res["country_code"] == "US"


def test_excluded_codes():
    # "MY" is excluded as a standalone word usually, but regex might catch it.
    # The current regex logic in country_inferrer.py excludes MY, ID, NO, etc. if they appear as plain words to avoid false positives.
    assert infer_country_from_remarks("This is MY server") is None
    # "MY" in brackets should work because regex looks for specific patterns or flags first.
    # Actually, the implementation likely prioritizes flags, then bracketed codes.
    res = infer_country_from_remarks("Malaysia [MY]")
    assert res["country_code"] == "MY"
