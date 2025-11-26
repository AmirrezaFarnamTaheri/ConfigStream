import io
import tarfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from configstream.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_version(runner):
    result = runner.invoke(main, ["--version"])
    # If not installed as package, this might fail. We accept 1 if it prints error about package.
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

        result = runner.invoke(main, ["merge", "--sources", "sources.txt", "--dry-run"])

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

        result = runner.invoke(main, ["merge", "--sources", "sources.txt"])

        assert result.exit_code == 1
        assert "Pipeline Failed" in result.output


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.status_code = 200

    def iter_content(self, chunk_size=8192):
        for i in range(0, len(self.payload), chunk_size):
            yield self.payload[i : i + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _tar_payload(edition: str):
    buf = io.BytesIO()
    content = f"{edition}-data".encode()
    with tarfile.open(fileobj=buf, mode="w:gz") as archive:
        info = tarfile.TarInfo(name=f"{edition}_20250101/{edition}.mmdb")
        info.size = len(content)
        archive.addfile(info, io.BytesIO(content))
    buf.seek(0)
    return buf.read()


def test_update_databases_prefers_maxmind(monkeypatch, runner):
    payloads = iter(
        [
            _tar_payload("GeoLite2-City"),
            _tar_payload("GeoLite2-ASN"),
        ]
    )

    def fake_get(url, stream=True, timeout=120):
        return FakeResponse(next(payloads))

    monkeypatch.setattr("configstream.cli.requests.get", fake_get)

    with runner.isolated_filesystem():
        result = runner.invoke(
            main, ["update-databases"], env={"MAXMIND_LICENSE_KEY": "abc123"}
        )
        assert result.exit_code == 0
        assert Path("data/GeoLite2-City.mmdb").is_file()
        assert Path("data/GeoLite2-ASN.mmdb").is_file()


def test_update_databases_mirror_fallback(monkeypatch, runner):
    payloads = iter([b"city-bytes", b"asn-bytes"])

    def fake_get(url, stream=True, timeout=120):
        return FakeResponse(next(payloads))

    monkeypatch.setattr("configstream.cli.requests.get", fake_get)

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
    # Now that bot_cli.py exports run_bot, we can test it
    with patch("configstream.bot_cli.run_bot") as mock_run:
        result = runner.invoke(main, ["bot", "--token", "FAKE"])
        assert result.exit_code == 0
        mock_run.assert_called_with("FAKE")
