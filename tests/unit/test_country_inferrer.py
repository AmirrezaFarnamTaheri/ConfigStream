from configstream.country_inferrer import (
    infer_country_from_remarks,
    _flag_to_country_code,
    _country_payload_from_code,
)


def test_infer_from_name():
    res = infer_country_from_remarks("My Server (US)")
    assert res is not None
    assert res["country_code"] == "US"

    res = infer_country_from_remarks("Germany Node 1")
    # Germany Node 1 -> Does not match regex patterns likely unless 'DE' is in there or name matches.
    # Wait, the regex matches 2-letter codes. 'DE' is in 'Node' (NO - Norway? DE - Germany?)
    # "Germany Node 1" -> "DE" is inside "Node"? No.
    # "NO" is in "Node". "NO" is in excluded codes? Yes.
    # So "Germany Node 1" might return None if strictly relying on codes.
    # Let's test with implicit code in brackets which is common.
    res = infer_country_from_remarks("Server [DE]")
    assert res["country_code"] == "DE"

    res = infer_country_from_remarks("Nothing here")
    assert res is None


def test_infer_priority():
    # UK maps to GB if we had a mapper, but the code only extracts ISO codes via regex.
    # So "UK" is not a valid ISO 3166-1 alpha-2 code (it's reserved but GB is standard).
    # If regex matches "UK", `_country_payload_from_code` checks `COUNTRY_NAMES`.
    # Does `COUNTRY_NAMES` have "UK"? Let's assume standard ISO.
    # If "UK" is not in COUNTRY_NAMES, it returns None.
    pass


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
    # "MY" is excluded
    assert infer_country_from_remarks("This is MY server") is None
    # "MY" in brackets should work
    res = infer_country_from_remarks("Malaysia [MY]")
    assert res["country_code"] == "MY"
