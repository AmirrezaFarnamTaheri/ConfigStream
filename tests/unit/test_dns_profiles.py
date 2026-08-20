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
    assert all(isinstance(ip, str) and "." in ip for ip in CLOUDFLARE_OPTIMIZED_IPS)


def test_singbox_dns_profile_structure():
    profile = build_singbox_dns_profile()
    assert "servers" in profile
    assert "rules" in profile

    servers = {s.get("tag"): s for s in profile["servers"]}
    assert "local_local" in servers
    assert "remote_dns" in servers
    assert "direct_dns" in servers
    assert "block_dns" not in servers
    assert "detour" not in servers["remote_dns"]

    # Sing-box 1.12+ typed DNS servers are emitted directly; hostname-based
    # DoH servers explicitly reference a bootstrap resolver.
    assert all("address" not in server for server in profile["servers"])
    assert servers["remote_dns"] == {
        "type": "https",
        "tag": "remote_dns",
        "server": "cloudflare-dns.com",
        "server_port": 443,
        "path": "/dns-query",
        "domain_resolver": "local_local",
    }
    assert servers["direct_dns"]["domain_resolver"] == "local_local"
    assert servers["local_local"]["type"] == "udp"
    assert servers["local_local"]["server"] == "1.1.1.1"

    routed_rules = [rule for rule in profile["rules"] if rule.get("action") == "route"]
    assert routed_rules == [
        {
            "domain": ["sing_box-ProxyChain"],
            "action": "route",
            "server": "local_local",
        },
        {
            "clash_mode": "Global",
            "action": "route",
            "server": "remote_dns",
        },
        {
            "clash_mode": "Direct",
            "action": "route",
            "server": "direct_dns",
        },
        {
            "rule_set": ["geosite-private", "geosite-ir"],
            "action": "route",
            "server": "direct_dns",
        },
    ]

    ad_rules = [
        rule
        for rule in profile["rules"]
        if "geosite-category-ads-all" in rule.get("rule_set", [])
    ]
    assert ad_rules == [
        {
            "rule_set": ["geosite-category-ads-all"],
            "action": "predefined",
            "rcode": "NOERROR",
        }
    ]


def test_clash_dns_profile():
    profile = build_clash_dns_profile()
    assert profile["enable"] is True
    assert "nameserver" in profile
    assert "fallback" in profile
