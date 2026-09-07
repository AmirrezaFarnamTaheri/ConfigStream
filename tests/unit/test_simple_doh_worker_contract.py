# SPDX-License-Identifier: AGPL-3.0-or-later
"""Security contract for the compact Cloudflare DoH relay."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "tools" / "workers" / "simple_doh.js"


def test_simple_doh_does_not_forward_client_headers_or_follow_redirects() -> None:
    text = WORKER.read_text(encoding="utf-8")

    assert "new Headers(request.headers)" not in text
    assert "redirect: 'follow'" not in text
    assert "redirect: 'error'" in text
    assert "Authorization" not in text
    assert "Cookie" not in text


def test_simple_doh_bounds_wire_messages_and_failover() -> None:
    text = WORKER.read_text(encoding="utf-8")

    assert "MAX_DNS_REQUEST_SIZE = 4096" in text
    assert "MAX_DNS_RESPONSE_SIZE = 65535" in text
    assert "MAX_PROVIDER_ATTEMPTS = 2" in text
    assert "request.arrayBuffer()" in text
    assert "response.arrayBuffer()" in text
    assert "body = dnsRequest.body.slice(0)" in text


def test_simple_doh_only_forwards_dns_protocol_fields() -> None:
    text = WORKER.read_text(encoding="utf-8")

    assert "url.searchParams.size !== 1" in text
    assert "upstreamUrl.searchParams.set('dns', dnsRequest.dnsParam)" in text
    assert "POST Content-Type must be application/dns-message" in text
    assert "'Cache-Control': 'no-store'" in text


def test_simple_doh_uses_consistent_standard_upstreams() -> None:
    text = WORKER.read_text(encoding="utf-8")

    assert "cloudflare-dns.com/dns-query" in text
    assert "dns.google/dns-query" in text
    assert "adblock.dns.mullvad.net" not in text
    assert "freedns.controld.com" not in text
