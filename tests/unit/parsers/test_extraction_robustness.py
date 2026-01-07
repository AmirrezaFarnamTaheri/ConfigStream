import pytest
from configstream.parsers.extraction import is_plausible_proxy_config

def test_is_plausible_proxy_config_relaxed():
    # A standard VLESS config with lots of Base64 noise
    # This string is mostly alphanumeric but has some special chars in parameters
    vless_config = (
        "vless://uuid@example.com:443?security=reality&encryption=none&pbk=789&fp=chrome&type=grpc&serviceName=grpc#Iran-Tehran"
    )
    assert is_plausible_proxy_config(vless_config) is True

    # A very noisy config (simulated Base64 dense payload)
    # 98% rule check.
    # "Abc" + 100 * "!" -> 3 chars vs 100 chars. 100/103 = 0.97. Should PASS with 0.98 limit.
    noisy_config_pass = "vmess://" + "A" * 5 + "!" * 100
    # 100 special chars, 5 normal. Total 105. 100/105 = 0.952.
    # Wait, '!' is in the allowed set! ":-_./@#%?&=+,;()~[]!*'|$"
    # So '!' does NOT count as special/bad.

    # We need chars NOT in the allowed set.
    # Allowed: : - _ . / @ # % ? & = + , ; ( ) ~ [ ] ! * ' | $
    # Not allowed: ^ < > ` " \ { }

    # Let's try a string with '^' which is NOT allowed.
    bad_chars = "^" * 99
    good_chars = "A"
    bad_config = "vmess://" + good_chars + bad_chars
    # 99 bad, 1 good. 99/100 = 0.99. Should FAIL.
    assert is_plausible_proxy_config(bad_config) is False

    # Borderline case
    # 97 bad, 3 good. 97/100 = 0.97. Should PASS (<= 0.98)
    borderline_config = "vmess://" + "ABC" + "^" * 97
    assert is_plausible_proxy_config(borderline_config) is True

    # Real world case: VLESS with complex params including allowed special chars
    # encryption=none&pbk=...&fp=chrome
    # & = allowed
    # ? = allowed
    # = = allowed
    real_config = "vless://abcd@1.2.3.4:443?query=val&fragment=#tag"
    assert is_plausible_proxy_config(real_config) is True

def test_is_plausible_proxy_config_basics():
    assert is_plausible_proxy_config("http://1.2.3.4:8080") is True
    assert is_plausible_proxy_config("notaproxy") is False
    assert is_plausible_proxy_config("://missingprotocol") is False
