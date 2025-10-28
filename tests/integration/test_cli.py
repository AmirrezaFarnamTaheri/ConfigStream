import pytest
from click.testing import CliRunner
from configstream.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_merge_success(runner, mocker):
    mocker.patch("configstream.cli.pipeline.run_full_pipeline", return_value={"success": True})
    result = runner.invoke(
        cli, ["merge", "--sources", "tests/fixtures/sources.txt", "--output", "/tmp/"]
    )
    assert result.exit_code == 0
    assert "Pipeline completed successfully" in result.output


def test_cli_merge_failure(runner, mocker):
    mocker.patch(
        "configstream.cli.pipeline.run_full_pipeline",
        return_value={"success": False, "error": "Test error"},
    )
    result = runner.invoke(
        cli, ["merge", "--sources", "tests/fixtures/sources.txt", "--output", "/tmp/"]
    )
    assert result.exit_code != 0
    assert "Pipeline failed" in result.output


def test_cli_retest_success(runner, mocker, tmp_path):
    mocker.patch("configstream.cli.pipeline.run_full_pipeline", return_value={"success": True})
    proxies_file = tmp_path / "proxies.json"
    proxies_file.write_text(
        '[{"config": "vmess://foo", "protocol": "vmess", "address": "1.1.1.1", "port": 443}]'
    )

    result = runner.invoke(cli, ["retest", "--input", str(proxies_file), "--output", str(tmp_path)])
    assert result.exit_code == 0
    assert "Retest completed successfully" in result.output


def test_cli_retest_failure(runner, mocker, tmp_path):
    mocker.patch(
        "configstream.cli.pipeline.run_full_pipeline",
        return_value={"success": False, "error": "Test error"},
    )
    proxies_file = tmp_path / "proxies.json"
    proxies_file.write_text(
        '[{"config": "vmess://foo", "protocol": "vmess", "address": "1.1.1.1", "port": 443}]'
    )

    result = runner.invoke(cli, ["retest", "--input", str(proxies_file), "--output", str(tmp_path)])
    assert result.exit_code != 0
    assert "Test error" in result.output


def test_cli_invalid_command(runner):
    result = runner.invoke(cli, ["invalid-command"])
    assert result.exit_code != 0
    assert "No such command" in result.output


def test_cli_update_databases_success(runner, mocker):
    mocker.patch("configstream.cli.download_geoip_dbs", return_value=True)
    result = runner.invoke(cli, ["update-databases"])
    assert result.exit_code == 0
    assert "All databases updated successfully" in result.output


def test_cli_update_databases_failure(runner, mocker):
    mocker.patch("configstream.cli.download_geoip_dbs", return_value=False)
    result = runner.invoke(cli, ["update-databases"])
    assert result.exit_code == 0
    assert "Some databases failed to update" in result.output


def test_cli_merge_no_sources_file(runner):
    result = runner.invoke(cli, ["merge", "--sources", "nonexistent.txt", "--output", "/tmp/"])
    assert result.exit_code != 0
    assert "Invalid value for '--sources'" in result.output


def test_cli_merge_empty_sources_file(runner, fs):
    fs.create_file("empty_sources.txt")
    result = runner.invoke(cli, ["merge", "--sources", "empty_sources.txt", "--output", "/tmp/"])
    assert result.exit_code != 0
    assert "No sources found" in result.output


def test_cli_merge_show_metrics(runner, mocker):
    mocker.patch(
        "configstream.cli.pipeline.run_full_pipeline",
        return_value={"success": True, "metrics": {"total_seconds": 1.23}},
    )
    result = runner.invoke(
        cli,
        ["merge", "--sources", "tests/fixtures/sources.txt", "--output", "/tmp/", "--show-metrics"],
    )
    assert result.exit_code == 0
    assert "Performance metrics" in result.output
    assert "Total time: 1.23s" in result.output


def test_cli_retest_invalid_json(runner, fs, mocker):
    fs.create_file("invalid_proxies.json", contents='[{"invalid": "proxy"}]')
    mocker.patch("configstream.cli.pipeline.run_full_pipeline", return_value={"success": True})
    result = runner.invoke(cli, ["retest", "--input", "invalid_proxies.json", "--output", "/tmp/"])
    assert "Skipped 1 invalid proxy definitions" in result.output


def test_cli_retest_no_valid_proxies(runner, fs):
    fs.create_file("no_valid_proxies.json", contents='[{"invalid": "proxy"}]')
    result = runner.invoke(cli, ["retest", "--input", "no_valid_proxies.json", "--output", "/tmp/"])
    assert result.exit_code != 0
    assert "No proxies found" in result.output


def test_cli_retest_show_metrics(runner, mocker, tmp_path):
    mocker.patch(
        "configstream.cli.pipeline.run_full_pipeline",
        return_value={"success": True, "metrics": {"total_seconds": 2.34}},
    )
    proxies_file = tmp_path / "proxies.json"
    proxies_file.write_text(
        '[{"config": "vmess://foo", "protocol": "vmess", "address": "1.1.1.1", "port": 443}]'
    )

    result = runner.invoke(
        cli,
        [
            "retest",
            "--input",
            str(proxies_file),
            "--output",
            str(tmp_path),
            "--show-metrics",
        ],
    )
    assert result.exit_code == 0
    assert "Performance metrics" in result.output
    assert "Total time: 2.34s" in result.output
