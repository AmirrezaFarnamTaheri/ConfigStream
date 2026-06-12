from configstream.dns_profiles import (
    build_singbox_dns_profile,
    build_clash_dns_profile,
    IRAN_INFRASTRUCTURE_DNS,
    CLOUDFLARE_OPTIMIZED_IPS,
)


def test_infrastructure_dns_list():
    assert "217.218.127.127" in IRAN_INFRASTRUCTURE_DNS
    assert len(IRAN_INFRASTRUCTURE_DNS) > 10


def test_cloudflare_optimized_ips():
    assert len(CLOUDFLARE_OPTIMIZED_IPS) > 5
    # Verify entries are valid IP-like strings
    assert all(isinstance(ip, str) and "." in ip for ip in CLOUDFLARE_OPTIMIZED_IPS)


def test_singbox_dns_profile_structure():
    profile = build_singbox_dns_profile()
    assert "servers" in profile
    assert "rules" in profile

    # Check for required server tags (standard "address" format)
    servers = {s.get("tag"): s for s in profile["servers"]}
    assert "local_local" in servers
    assert "remote_dns" in servers
    assert "direct_dns" in servers
    assert "block_dns" in servers

    # Verify servers use "address" field (not "type"/"server" which is 1.12+ only)
    for s in profile["servers"]:
        assert "address" in s, f"Server {s.get('tag')} missing 'address' field"


def test_clash_dns_profile():
    profile = build_clash_dns_profile()
    assert profile["enable"] is True
    assert "nameserver" in profile
    assert "fallback" in profile
