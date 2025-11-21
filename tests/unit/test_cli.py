from click.testing import CliRunner
from configstream.cli import main
from unittest.mock import patch, MagicMock, AsyncMock

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output

def test_cli_merge_dry_run():
    # run_full_pipeline is async, so we should use AsyncMock
    with patch("configstream.cli.run_full_pipeline", new_callable=AsyncMock) as mock_pipeline:
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stats = {
            "duration": 1.5,
            "fetched_lines": 10,
            "tested": 5,
            "working": 2,
            "geo_resolved": 2
        }
        mock_pipeline.return_value = mock_result

        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("s.txt", "w") as f:
                f.write("http://example.com")

            result = runner.invoke(main, ["merge", "--dry-run", "--sources", "s.txt"])

            if result.exit_code != 0:
                print(result.output)
                print(result.exception)

            assert result.exit_code == 0
            mock_pipeline.assert_called_once()

def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "version" in result.output
