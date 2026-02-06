import pytest
from configstream.dns_profiles import (
    build_singbox_dns_profile, 
    build_clash_dns_profile, 
    IRAN_INFRASTRUCTURE_DNS,
    CLOUDFLARE_OPTIMIZED_IPS
)

def test_infrastructure_dns_list():
    assert "217.218.127.127" in IRAN_INFRASTRUCTURE_DNS
    assert len(IRAN_INFRASTRUCTURE_DNS) > 10

def test_cloudflare_optimized_ips():
    assert "108.162.192.0" in CLOUDFLARE_OPTIMIZED_IPS
    assert len(CLOUDFLARE_OPTIMIZED_IPS) > 5

def test_singbox_dns_profile_structure():
    profile = build_singbox_dns_profile()
    assert "servers" in profile
    assert "rules" in profile
    
    # Check for new keys
    servers = {s.get("tag"): s for s in profile["servers"]}
    assert "local_local" in servers
    assert "hosts_dns" in servers
    assert "remote_dns" in servers
    
    # Check predefined hosts
    hosts_server = servers["hosts_dns"]
    assert "predefined" in hosts_server
    assert "cloudflare-dns.com" in hosts_server["predefined"]
    
    # Verify optimized IPs are used
    cf_ips = hosts_server["predefined"]["cloudflare-dns.com"]
    assert any(ip in CLOUDFLARE_OPTIMIZED_IPS for ip in cf_ips)

def test_clash_dns_profile():
    profile = build_clash_dns_profile()
    assert profile["enable"] is True
    assert "nameserver" in profile
    assert "fallback" in profile
