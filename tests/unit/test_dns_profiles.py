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

    # Keep the generated legacy-input profile migration-safe for modern sing-box:
    # no removed rcode transport and no forced proxy selector that may be absent
    # in zero-proxy/degraded artifacts.
    servers = {s.get("tag"): s for s in profile["servers"]}
    assert "local_local" in servers
    assert "remote_dns" in servers
    assert "direct_dns" in servers
    assert "block_dns" not in servers
    assert "detour" not in servers["remote_dns"]
    assert all(
        not str(s.get("address", "")).startswith("rcode://") for s in servers.values()
    )

    # Verify servers use the legacy input "address" field; release finalization
    # is responsible for migrating these into typed 1.12+ server objects.
    for server in profile["servers"]:
        assert (
            "address" in server
        ), f"Server {server.get('tag')} missing 'address' field"

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
