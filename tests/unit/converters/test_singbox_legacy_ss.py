from configstream.converters.singbox import _sanitize_ss_method, VALID_SS_METHODS

def test_legacy_ss_methods_accepted():
    """Test that legacy stream ciphers are now accepted."""
    assert "aes-256-cfb" in VALID_SS_METHODS
    assert _sanitize_ss_method("aes-256-cfb") == "aes-256-cfb"
    assert _sanitize_ss_method("rc4-md5") == "rc4-md5"
    assert _sanitize_ss_method("chacha20-ietf") == "chacha20-ietf"

def test_garbage_still_rejected():
    assert _sanitize_ss_method("garbage") is None
