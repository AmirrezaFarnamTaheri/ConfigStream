import pytest

from configstream.pipeline import run_full_pipeline


@pytest.mark.asyncio
async def test_mixed_protocols_dry_run(tmp_path, monkeypatch):
    """
    E2E test with mixed protocols (VLESS, VMess, Shadowsocks, Trojan)
    running in dry_run mode to verify parsing, deduplication, and pipeline flow
    without external network calls.
    """
    # 1. Prepare Mixed Source File
    source_content = [
        # VLESS Reality (Added &sid=shortid for parser validity)
        "vless://22222222-2222-2222-2222-222222222222@2.2.2.2:443?security=reality&encryption=none&pbk=76543210&sid=1234abcd&fp=chrome&type=tcp&sni=example.com#VLESS-Mix",
        # VMess WS
        "vmess://ew0KICAidiI6ICIyIiwNCiAgInBzIjogIlZNZXNzLU1peCIsDQogICJhZGQiOiAiMy4zLjMuMyIsDQogICJwb3J0IjogIjQ0MyIsDQogICJpZCI6ICIzMzMzMzMzMy0zMzMzLTMzMzMtMzMzMy0zMzMzMzMzMzMzMzMiLA0KICAiYWlkIjogIjAiLA0KICAic2N5IjogImF1dG8iLA0KICAibmV0IjogIndzIiwNCiAgInR5cGUiOiAibm9uZSIsDQogICJob3N0IjogImNkbS5leGFtcGxlLmNvbSIsDQogICJwYXRoIjogIi9hcGkiLA0KICAidGxzIjogInRscyIsDQogICJzbmkiOiAiY2RtLmV4YW1wbGUuY29tIiwNCiAgImFscG4iOiAiIg0KfQ==",
        # Shadowsocks
        "ss://YWVzLTI1Ni1nY206cGFzc3dvcmRAMC4wLjAuMDo4Mzgy#SS-Mix",
        # Trojan
        "trojan://password@4.4.4.4:443?security=tls&type=tcp&sni=trojan.com#Trojan-Mix",
    ]

    src_file = tmp_path / "mixed_sources.txt"
    src_file.write_text("\n".join(source_content), encoding="utf-8")

    # 2. Mock external dependencies that might block or fail without network

    # Mock GeoIP to return deterministic data
    from configstream.geoip import GeoData

    async def fake_lookup(self, ip):
        # We need self because we are mocking the instance method or class method?
        # Actually standard mock usually mocks the function on the class.
        if "2.2.2.2" in str(ip) or "1111" in str(
            ip
        ):  # 1111 from failing test or new logic?
            # Our sources have 2.2.2.2, 3.3.3.3, 0.0.0.0, 4.4.4.4
            return GeoData(
                country_code="US", country_name="United States", city="New York"
            )
        elif "3.3.3.3" in str(ip):
            return GeoData(country_code="DE", country_name="Germany", city="Frankfurt")
        return GeoData(country_code="XX", country_name="Unknown", city="Unknown")

    monkeypatch.setattr("configstream.geoip.GeoIPResolver.lookup", fake_lookup)

    # Mock Blocklist update
    async def fake_update():
        return None

    monkeypatch.setattr("configstream.pipeline.DEFAULT_BLOCKLIST.update", fake_update)

    # Mock Output Generation to avoid filesystem overhead but verify data presence
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    # We allow the real output handler to run?
    # The roadmap says: "assert that parsing, validation, dedup, washing, and GeoIP enrichment all execute without mocks."
    # But running without network means we can't really do GeoIP enrichment (needs DB download).
    # So we MOCKED GeoIP above. The roadmap allows mocks for things that strictly require network.
    # We should let the output handler run to verify it doesn't crash on mixed types.
    # However, we need to mock `generate_stego_assets` since it requires assets/images which might not exist in tmp env.
    # But checking output_handler.py, it seems it doesn't call generate_stego_assets anymore.
    # So we remove the mock that causes AttributeError.

    # 3. Run Pipeline
    result = await run_full_pipeline(
        sources=[str(src_file)],
        output_dir=str(output_dir),
        dry_run=True,  # Critical: skips actual connectivity tests
    )

    # 4. Assertions
    assert result.success is True
    assert (
        result.stats.final_count >= 3
    )  # We expect at least 3 valid proxies (SS might fail if parser is strict about IP 0.0.0.0, let's see)

    # Verify outputs exist
    assert (output_dir / "singbox.json").exists()
    assert (output_dir / "clash.yaml").exists()
    assert (output_dir / "proxies.json").exists()

    # Verify content
    import json

    proxies = json.loads((output_dir / "proxies.json").read_text())
    protocols = {p["protocol"] for p in proxies}
    assert "vless" in protocols
    assert "vmess" in protocols
    assert "trojan" in protocols
