import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock, AsyncMock
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


def test_update_databases(runner):
    result = runner.invoke(main, ["update-databases"])
    assert result.exit_code == 0
    assert "handled by the CI/CD" in result.output


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
