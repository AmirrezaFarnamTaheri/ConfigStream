# SPDX-License-Identifier: AGPL-3.0-or-later
import io
import re
import tarfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx
from click.testing import CliRunner

from configstream.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_version(runner):
    result = runner.invoke(main, ["--version"])
    if result.exit_code != 0:
        assert "not installed" in str(result.exception) or "package_name" in str(
            result.exception
        )
    else:
        assert result.exit_code == 0
        assert "version" in result.output


def test_merge_missing_sources(runner):
    with patch("pathlib.Path.exists", return_value=False):
        result = runner.invoke(main, ["merge", "--sources", "missing.txt"])
        assert result.exit_code == 1
        assert "not found" in result.output


def test_merge_success(runner):
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value="http://source1\n#comment\n"),
        patch(
            "configstream.cli.run_full_pipeline", new_callable=AsyncMock
        ) as mock_pipeline,
    ):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stats = {
            "duration": 1.0,
            "fetched_lines": 10,
            "tested": 5,
            "working": 5,
            "geo_resolved": 5,
        }
        mock_pipeline.return_value = mock_result

        result = runner.invoke(
            main,
            [
                "merge",
                "--sources",
                "sources.txt",
                "--dry-run",
                "--allow-unadmitted-sources",
            ],
        )

        assert result.exit_code == 0
        assert "Pipeline Completed Successfully" in result.output
        mock_pipeline.assert_called_once()


def test_merge_failure(runner):
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value="http://source1"),
        patch(
            "configstream.cli.run_full_pipeline", new_callable=AsyncMock
        ) as mock_pipeline,
    ):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "Test Failure"
        mock_pipeline.return_value = mock_result

        result = runner.invoke(
            main,
            ["merge", "--sources", "sources.txt", "--allow-unadmitted-sources"],
        )

        assert result.exit_code == 1
        assert "Pipeline Failed" in result.output


def _tar_payload(edition: str):
    buf = io.BytesIO()
    content = f"{edition}-data".encode()
    with tarfile.open(fileobj=buf, mode="w:gz") as archive:
        info = tarfile.TarInfo(name=f"{edition}_20250101/{edition}.mmdb")
        info.size = len(content)
        archive.addfile(info, io.BytesIO(content))
    buf.seek(0)
    return buf.read()


def test_update_databases_prefers_maxmind(runner):
    maxmind_payloads = {
        "GeoLite2-City": _tar_payload("GeoLite2-City"),
        "GeoLite2-ASN": _tar_payload("GeoLite2-ASN"),
    }

    def respond(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "edition_id=GeoLite2-City" in url:
            return httpx.Response(200, content=maxmind_payloads["GeoLite2-City"])
        if "edition_id=GeoLite2-ASN" in url:
            return httpx.Response(200, content=maxmind_payloads["GeoLite2-ASN"])
        if url.endswith("/geosite.db") or url.endswith("/geoip.db"):
            return httpx.Response(200, content=b"db-bytes")
        raise AssertionError(f"Unexpected download URL: {url}")

    with respx.mock(assert_all_called=False) as router:
        router.get(re.compile(r"https://.*")).mock(side_effect=respond)
        with runner.isolated_filesystem():
            result = runner.invoke(
                main, ["update-databases"], env={"MAXMIND_LICENSE_KEY": "abc123"}
            )
            assert result.exit_code == 0
            assert Path("data/GeoLite2-City.mmdb").is_file()
            assert Path("data/GeoLite2-ASN.mmdb").is_file()


def test_update_databases_mirror_fallback(runner):
    def respond(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/GeoLite2-City.mmdb"):
            return httpx.Response(200, content=b"city-bytes")
        if url.endswith("/GeoLite2-ASN.mmdb"):
            return httpx.Response(200, content=b"asn-bytes")
        if url.endswith("/geosite.db") or url.endswith("/geoip.db"):
            return httpx.Response(200, content=b"db-bytes")
        raise AssertionError(f"Unexpected download URL: {url}")

    with respx.mock(assert_all_called=False) as router:
        router.get(re.compile(r"https://.*")).mock(side_effect=respond)
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["update-databases"])
            assert result.exit_code == 0
            assert Path("data/GeoLite2-City.mmdb").read_bytes() == b"city-bytes"
            assert Path("data/GeoLite2-ASN.mmdb").read_bytes() == b"asn-bytes"


def test_generate_warp(runner):
    with patch(
        "configstream.cli.generate_warp_proxy", new_callable=AsyncMock
    ) as mock_gen:
        mock_p = MagicMock()
        mock_p.protocol = "wireguard"
        mock_p.details = {}
        mock_p.config = "conf"
        mock_gen.return_value = mock_p

        result = runner.invoke(main, ["generate-warp", "--count", "1"])
        assert result.exit_code == 0
        assert "Protocol: wireguard" in result.output


def test_bot_command(runner):
    with patch("configstream.bot_cli.run_bot") as mock_run:
        result = runner.invoke(main, ["bot", "--token", "FAKE"])
        assert result.exit_code == 0
        mock_run.assert_called_with("FAKE")


class PartialFailureStream(httpx.SyncByteStream):
    def __iter__(self):
        yield b"partial"
        raise httpx.ReadError("connection interrupted")


def test_update_databases_does_not_publish_partial_downloads(runner):
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=PartialFailureStream())

    with respx.mock(assert_all_called=False) as router:
        router.get(re.compile(r"https://.*")).mock(side_effect=respond)
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["update-databases"])

            assert result.exit_code == 1
            assert not Path("data/GeoLite2-City.mmdb").exists()
            assert not Path("data/GeoLite2-ASN.mmdb").exists()
            assert not Path("data/singbox/geosite.db").exists()
            assert not Path("data/singbox/geoip.db").exists()
            assert not list(Path("data").rglob(".*.tmp"))
