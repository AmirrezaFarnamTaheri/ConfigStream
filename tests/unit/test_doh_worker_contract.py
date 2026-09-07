# SPDX-License-Identifier: AGPL-3.0-or-later
"""Security and DNS-wire contracts for the Cloudflare DoH worker variants."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKERS = [
    ROOT / "tools" / "workers" / "doh_proxy.js",
    ROOT / "tools" / "workers" / "doh_path.js",
]


def test_doh_workers_bound_requests_responses_and_failover() -> None:
    for path in WORKERS:
        text = path.read_text(encoding="utf-8")
        assert "MAX_DNS_REQUEST_SIZE = 4096" in text
        assert "MAX_DNS_RESPONSE_SIZE = 65535" in text
        assert "MAX_PROVIDER_ATTEMPTS = 2" in text
        assert "Promise.any" not in text
        assert "DECOY_REQUEST_PROBABILITY" not in text
        assert "redirect: 'error'" in text


def test_doh_workers_validate_dns_wire_identity() -> None:
    for path in WORKERS:
        text = path.read_text(encoding="utf-8")
        assert "validateDNSQuery(wire)" in text
        assert "validateDNSResponse(dnsRequest.wire, responseWire)" in text
        assert "DNS transaction ID mismatch" in text
        assert "DNS request has no questions" in text


def test_doh_workers_do_not_fake_dns_cache_ttls_or_forward_spoofed_ips() -> None:
    for path in WORKERS:
        text = path.read_text(encoding="utf-8")
        assert "calculateDynamicTTL" not in text
        assert "dnsCache" not in text
        assert "X-Forwarded-For" not in text
        assert "X-Real-IP" not in text
        assert "'Cache-Control': 'no-store'" in text


def test_doh_workers_keep_expected_deployment_entrypoints() -> None:
    proxy = WORKERS[0].read_text(encoding="utf-8")
    pages = WORKERS[1].read_text(encoding="utf-8")

    assert "addEventListener('fetch'" in proxy
    assert "export async function onRequest(context)" in pages
    assert "url.pathname === '/apple'" in proxy
    assert "url.pathname === '/apple'" in pages
