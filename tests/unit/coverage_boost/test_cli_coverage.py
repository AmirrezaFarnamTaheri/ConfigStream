import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from configstream.cli import main as cli, setup_logging as cli_setup_logging
from click.testing import CliRunner


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_setup_logging_verbose():
    with patch("logging.basicConfig") as mock_basic_config:
        cli_setup_logging(True)
        # Check if level was DEBUG (10)
        args, kwargs = mock_basic_config.call_args
        assert kwargs["level"] == 10


def test_cli_setup_logging_default():
    with patch("logging.basicConfig") as mock_basic_config:
        cli_setup_logging(False)
        # Check if level was INFO (20)
        args, kwargs = mock_basic_config.call_args
        assert kwargs["level"] == 20


def test_cli_version(runner):
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "version" in result.output


def test_cli_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output


@patch("configstream.cli.run_full_pipeline")
def test_cli_merge_command(mock_pipeline, runner):
    # Mock stats object
    stats_mock = MagicMock()
    # Configure attributes so getattr(stats, key) returns float/int, not MagicMock
    stats_mock.duration = 1.5
    stats_mock.fetched_lines = 100
    stats_mock.tested = 50
    stats_mock.working = 40
    stats_mock.geo_resolved = 30
    stats_mock.to_dict.return_value = {
        "duration": 1.5,
        "fetched_lines": 100,
        "tested": 50,
        "working": 40,
        "geo_resolved": 30,
    }

    # Mock pipeline result
    result_mock = MagicMock()
    result_mock.success = True
    result_mock.stats = stats_mock
    result_mock.error = None

    mock_pipeline.return_value = result_mock
    mock_pipeline.side_effect = AsyncMock(return_value=result_mock)

    with runner.isolated_filesystem():
        with open("sources.txt", "w") as f:
            f.write("https://example.com/subs")

        result = runner.invoke(
            cli, ["merge", "--sources", "sources.txt", "--max-workers", "10"]
        )

        if result.exit_code != 0:
            print(f"CLI Output: {result.output}")
            print(f"CLI Exception: {result.exception}")

        assert result.exit_code == 0


@patch("configstream.cli.run_full_pipeline")
def test_cli_merge_command_fail(mock_pipeline, runner):
    result_mock = MagicMock()
    result_mock.success = False
    result_mock.error = "Simulated Failure"

    mock_pipeline.side_effect = AsyncMock(return_value=result_mock)

    with runner.isolated_filesystem():
        with open("sources.txt", "w") as f:
            f.write("https://example.com")

        result = runner.invoke(cli, ["merge", "--sources", "sources.txt"])
        assert result.exit_code == 1
        assert "Simulated Failure" in result.output
