import pytest
from configstream.models import Proxy
from configstream.output import (
    generate_base64_subscription,
    generate_clash_config,
    generate_singbox_config,
    generate_shadowrocket_subscription,
    generate_quantumult_config,
    generate_surge_config,
)


@pytest.fixture
def sample_proxies():
    """Fixture for a list of sample Proxy objects."""
    return [
        Proxy(
            config="vmess://ewogICJ2IjogIjIiLAogICJwcyI6ICJVUy1WTWVzcyIsCiAgImFkZCI6ICJ1cy5leGFtcGxlLmNvbSIsCiAgInBvcnQiOiA0NDMsCiAgImlkIjogInRlc3QtdXVpZCIsCiAgIm5ldCI6ICJ3cyIsCiAgInR5cGUiOiAibm9uZSIsCiAgImhvc3QiOiAiIiwKICAicGF0aCI6ICIvIiwKICAidGxzIjogIm5vbmUiCn0=",
            protocol="vmess",
            address="us.example.com",
            port=443,
            remarks="US-VMess",
            details={"uuid": "test-uuid"},
            is_working=True,
        ),
        Proxy(
            config="ss://YWVzLTI1Ni1nY206dGVzdC1wYXNzd29yZA==",
            protocol="ss",
            address="gb.example.com",
            port=8443,
            remarks="GB-SS",
            details={"method": "aes-256-gcm", "password": "test-password"},
            is_working=True,
        ),
    ]


def test_generate_base64_subscription(sample_proxies):
    """Test the base64 subscription generation."""
    result = generate_base64_subscription(sample_proxies)
    expected_configs = [p.config for p in sample_proxies if p.is_working]
    assert result == "\n".join(expected_configs)


def test_generate_clash_config(sample_proxies):
    """Test the Clash config generation."""
    result = generate_clash_config(sample_proxies)
    assert "proxies:" in result
    assert "US-VMess" in result
    assert "GB-SS" in result


def test_generate_singbox_config(sample_proxies):
    """Test the SingBox config generation."""
    result = generate_singbox_config(sample_proxies)
    import json

    data = json.loads(result)
    assert "outbounds" in data
    assert len(data["outbounds"]) > 0


def test_generate_shadowrocket_subscription_format(sample_proxies):
    """Test the ShadowRocket subscription generation for correct format."""
    result = generate_shadowrocket_subscription(sample_proxies)
    import base64

    decoded = base64.b64decode(result).decode("utf-8")
    lines = decoded.strip().split("\n")
    assert len(lines) == 2

    # Check that each line contains the raw config and does not have double scheme
    # e.g., "US-VMess = vmess://..." not "US-VMess = vmess://vmess://..."
    for line, proxy in zip(lines, sample_proxies):
        assert f"{proxy.remarks} = {proxy.config}" == line
        scheme_count = line.count("://")
        assert (
            scheme_count == 1
        ), f"Expected exactly one '://' in Shadowrocket line, found {scheme_count}: {line}"


def test_generate_quantumult_config(sample_proxies):
    """Test the Quantumult config generation."""
    result = generate_quantumult_config(sample_proxies)
    assert "[SERVER]" in result


def test_generate_surge_config(sample_proxies):
    """Test the Surge config generation."""
    result = generate_surge_config(sample_proxies)
    assert "[Proxy]" in result
