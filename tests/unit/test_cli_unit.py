import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from configstream.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_merge_command_success(runner):
    """Test the merge command with valid inputs."""
    with patch("configstream.pipeline.run_full_pipeline") as mock_run_pipeline:
        mock_run_pipeline.return_value = {"success": True, "stats": {}, "output_files": {}}
        with runner.isolated_filesystem():
            with open("sources.txt", "w") as f:
                f.write("http://example.com/source")
            result = runner.invoke(cli, ["merge", "--sources", "sources.txt", "--output", "output"])
            assert result.exit_code == 0
            assert "Pipeline completed successfully" in result.output


def test_merge_command_failure(runner):
    """Test the merge command when the pipeline fails."""
    with patch("configstream.pipeline.run_full_pipeline") as mock_run_pipeline:
        mock_run_pipeline.return_value = {
            "success": False,
            "error": "Test error",
            "stats": {},
            "output_files": {},
        }
        with runner.isolated_filesystem():
            with open("sources.txt", "w") as f:
                f.write("http://example.com/source")
            result = runner.invoke(cli, ["merge", "--sources", "sources.txt", "--output", "output"])
            assert result.exit_code != 0
            assert "Pipeline failed" in result.output
            assert "Test error" in result.output


def test_update_databases_command(runner):
    """Test the update-databases command."""
    with patch("configstream.cli.download_geoip_dbs") as mock_download:
        result = runner.invoke(cli, ["update-databases"])
        assert result.exit_code == 0
        assert "Updating GeoIP databases" in result.output
        mock_download.assert_called_once()
