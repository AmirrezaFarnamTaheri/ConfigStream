# SPDX-License-Identifier: AGPL-3.0-or-later
"""Apply the one-time zero-working shard remediation to the current checkout."""

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"Expected one match in {path}, found {count}: {old[:100]!r}"
        )
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    config_path = Path("src/configstream/config.py")
    config_text = config_path.read_text(encoding="utf-8")
    if "class AppSettings(BaseSettings):" not in config_text:
        raise RuntimeError("AppSettings is incomplete")
    if "FAIL_ON_ZERO_WORKING: bool = True" in config_text:
        config_path.write_text(
            config_text.replace(
                "FAIL_ON_ZERO_WORKING: bool = True",
                "FAIL_ON_ZERO_WORKING: bool = False",
                1,
            ),
            encoding="utf-8",
        )
    elif "FAIL_ON_ZERO_WORKING: bool = False" not in config_text:
        raise RuntimeError("FAIL_ON_ZERO_WORKING is missing")

    Path("src/configstream/pipeline/policy.py").write_text(
        '''# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pipeline outcome policies independent from security validation."""


def should_fail_zero_working(
    *,
    tested: int,
    working: int,
    time_limited: bool,
    fail_on_zero_working: bool,
) -> bool:
    """Return whether a completed run with tests but no successes must fail."""
    return (
        bool(fail_on_zero_working)
        and int(tested) > 0
        and int(working) == 0
        and not bool(time_limited)
    )
''',
        encoding="utf-8",
    )

    replace_once(
        "src/configstream/pipeline/core.py",
        "from configstream.config import AppSettings\n",
        "from configstream.config import AppSettings\n"
        "from configstream.pipeline.policy import should_fail_zero_working\n",
    )
    replace_once(
        "src/configstream/pipeline/core.py",
        "        time_limit_seconds: Optional[int] = None,\n"
        "    ) -> \"StandardPipeline\":\n",
        "        time_limit_seconds: Optional[int] = None,\n"
        "        fail_on_zero_working: Optional[bool] = None,\n"
        "    ) -> \"StandardPipeline\":\n",
    )
    replace_once(
        "src/configstream/pipeline/core.py",
        "        settings = AppSettings()\n"
        "        settings.validate_settings()\n",
        "        settings = AppSettings()\n"
        "        if fail_on_zero_working is not None:\n"
        "            settings.FAIL_ON_ZERO_WORKING = bool(fail_on_zero_working)\n"
        "        settings.validate_settings()\n",
    )
    replace_once(
        "src/configstream/pipeline/core.py",
        '''            should_fail = (
                (
                    self.context.strict_security
                    or bool(
                        getattr(self.context.settings, "FAIL_ON_ZERO_WORKING", False)
                    )
                )
                and bool(_zero_working)
                and not stats.time_limited
            )
''',
        '''            should_fail = should_fail_zero_working(
                tested=stats.tested,
                working=stats.working,
                time_limited=stats.time_limited,
                fail_on_zero_working=bool(
                    getattr(self.context.settings, "FAIL_ON_ZERO_WORKING", False)
                ),
            )
''',
    )
    replace_once(
        "src/configstream/pipeline/core.py",
        "0 working proxies detected and strict mode is enabled; marking pipeline result as failed.",
        "0 working proxies detected and FAIL_ON_ZERO_WORKING is enabled; marking pipeline result as failed.",
    )
    replace_once(
        "src/configstream/pipeline/core.py",
        "    proxies: Optional[List[Any]] = None,\n"
        ") -> PipelineResult:\n",
        "    proxies: Optional[List[Any]] = None,\n"
        "    fail_on_zero_working: Optional[bool] = None,\n"
        ") -> PipelineResult:\n",
    )
    replace_once(
        "src/configstream/pipeline/core.py",
        "        time_limit_seconds=time_limit_seconds,\n"
        "    )\n",
        "        time_limit_seconds=time_limit_seconds,\n"
        "        fail_on_zero_working=fail_on_zero_working,\n"
        "    )\n",
    )

    replace_once(
        "src/configstream/cli.py",
        '''@click.option(
    "--strict",
    is_flag=True,
    help="Fail the pipeline strictly if 0 working proxies are found.",
)
''',
        '''@click.option(
    "--fail-on-zero-working",
    "--strict",
    "fail_on_zero_working",
    is_flag=True,
    help=(
        "Fail when completed proxy tests produce zero working proxies. "
        "--strict remains as a backwards-compatible alias."
    ),
)
''',
    )
    replace_once(
        "src/configstream/cli.py",
        "    dry_run,\n"
        "    strict,\n"
        "    verbose,\n",
        "    dry_run,\n"
        "    fail_on_zero_working,\n"
        "    verbose,\n",
    )
    replace_once(
        "src/configstream/cli.py",
        "    if timeout is None:\n"
        "        timeout = settings.TEST_TIMEOUT\n",
        "    if timeout is None:\n"
        "        timeout = settings.TEST_TIMEOUT\n"
        "\n"
        "    effective_fail_on_zero_working = bool(\n"
        "        fail_on_zero_working or settings.FAIL_ON_ZERO_WORKING\n"
        "    )\n",
    )
    replace_once(
        "src/configstream/cli.py",
        "                time_limit_seconds=settings.BATCH_TIME_LIMIT_SECONDS,\n"
        "            )\n",
        "                time_limit_seconds=settings.BATCH_TIME_LIMIT_SECONDS,\n"
        "                fail_on_zero_working=effective_fail_on_zero_working,\n"
        "            )\n",
    )
    replace_once(
        "src/configstream/cli.py",
        '''            # CRITICAL: Fail pipeline if zero working proxies found
            # This ensures GitHub Actions workflow fails instead of silently passing with empty results.
            working = _get("working")
            if working == 0:
                console.print(
                    "\n[bold red]CRITICAL: Pipeline finished with 0 working proxies![/bold red]"
                )
                if (
                    strict or getattr(settings, "FAIL_ON_ZERO_WORKING", False)
                ) and not time_limited:
                    sys.exit(1)
                else:
                    console.print(
                        "[yellow]Continuing despite 0 working proxies (strict=False or time_limited=True)[/yellow]"
                    )
''',
        '''            working = _get("working")
            if working == 0:
                console.print(
                    "\n[yellow]No currently working proxies were detected. "
                    "Outputs were still generated; aggregate release validation "
                    "decides whether promotion is allowed.[/yellow]"
                )
''',
    )

    replace_once(
        ".github/workflows/main.yml",
        "            scripts/shard_sources.py \\\n"
        "            src/configstream/testers/python.py\n"
        "          pytest -q tests/unit/test_release_remediation.py --disable-warnings --maxfail=1\n",
        "            scripts/shard_sources.py \\\n"
        "            src/configstream/config.py \\\n"
        "            src/configstream/cli.py \\\n"
        "            src/configstream/pipeline/core.py \\\n"
        "            src/configstream/pipeline/policy.py \\\n"
        "            src/configstream/testers/python.py\n"
        "          pytest -q tests/unit/test_release_remediation.py tests/unit/test_zero_working_policy.py --disable-warnings --maxfail=1\n",
    )
    replace_once(
        ".github/workflows/main.yml",
        "          ALLOW_ACTIVE_SCANNING: \"false\"\n",
        "          ALLOW_ACTIVE_SCANNING: \"false\"\n"
        "          FAIL_ON_ZERO_WORKING: \"false\"\n",
    )

    env_replacements = {
        "MAX_LINES_PER_SOURCE=0": "MAX_LINES_PER_SOURCE=250000",
        "MAX_CONFIG_LINE_LENGTH=0": "MAX_CONFIG_LINE_LENGTH=262144",
        "MAX_SEEN_KEYS=0": "MAX_SEEN_KEYS=2000000",
        "MAX_B64_INPUT_SIZE=0": "MAX_B64_INPUT_SIZE=8388608",
        "MAX_B64_OUTPUT_SIZE=0": "MAX_B64_OUTPUT_SIZE=33554432",
        "MAX_OPENVPN_CONFIG_SIZE=0": "MAX_OPENVPN_CONFIG_SIZE=2097152",
        "MAX_RESPONSE_SIZE=0": "MAX_RESPONSE_SIZE=16777216",
        "# Worker Auto-Scaling (0 = auto-detect based on CPU cores)\nMAX_WORKERS=0": (
            "# Finite worker default; tune it for the deployment.\n"
            "MAX_WORKERS=128"
        ),
        "DNS_SAFE_RESOLVE_LIMIT=0": "DNS_SAFE_RESOLVE_LIMIT=100000",
    }
    for old, new in env_replacements.items():
        replace_once(".env.example", old, new)

    replace_once(
        "CHANGELOG.md",
        "## [Unreleased]\n",
        '''## [Unreleased]

- **Zero-working shard policy correction**:
  - Made zero-working failure opt-in and independent from strict security validation.
  - Preserved per-shard outputs when a shard has no currently working proxies while retaining the aggregate release gate as the promotion authority.
  - Added a backwards-compatible `--strict` alias for the explicit `--fail-on-zero-working` CLI option, finite example resource limits, and regression coverage.
''',
    )

    Path("tests/unit/test_zero_working_policy.py").write_text(
        '''# SPDX-License-Identifier: AGPL-3.0-or-later
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner
import pytest

import configstream.cli as cli
from configstream.config import AppSettings
from configstream.pipeline.policy import should_fail_zero_working


@pytest.mark.parametrize(
    ("tested", "working", "time_limited", "enabled", "expected"),
    [
        (100, 0, False, False, False),
        (100, 0, False, True, True),
        (100, 0, True, True, False),
        (0, 0, False, True, False),
        (100, 1, False, True, False),
    ],
)
def test_zero_working_policy(
    tested: int,
    working: int,
    time_limited: bool,
    enabled: bool,
    expected: bool,
) -> None:
    assert (
        should_fail_zero_working(
            tested=tested,
            working=working,
            time_limited=time_limited,
            fail_on_zero_working=enabled,
        )
        is expected
    )


def test_zero_working_is_fail_open_by_default() -> None:
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("FAIL_ON_ZERO_WORKING", None)
        assert AppSettings(_env_file=None).FAIL_ON_ZERO_WORKING is False


def test_zero_working_can_be_enabled_explicitly() -> None:
    with patch.dict(os.environ, {"FAIL_ON_ZERO_WORKING": "true"}, clear=False):
        assert AppSettings(_env_file=None).FAIL_ON_ZERO_WORKING is True


def test_env_example_uses_valid_finite_limits() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    settings = AppSettings(_env_file=repo_root / ".env.example")
    assert settings.MAX_LINES_PER_SOURCE == 250_000
    assert settings.MAX_CONFIG_LINE_LENGTH == 256 * 1024
    assert settings.MAX_SEEN_KEYS == 2_000_000
    assert settings.MAX_B64_INPUT_SIZE == 8 * 1024 * 1024
    assert settings.MAX_B64_OUTPUT_SIZE == 32 * 1024 * 1024
    assert settings.MAX_OPENVPN_CONFIG_SIZE == 2 * 1024 * 1024
    assert settings.MAX_RESPONSE_SIZE == 16 * 1024 * 1024
    assert settings.MAX_WORKERS == 128
    assert settings.DNS_SAFE_RESOLVE_LIMIT == 100_000


def test_source_shards_are_explicitly_fail_open() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    workflow = (repo_root / ".github/workflows/main.yml").read_text(
        encoding="utf-8"
    )
    bounded_shard = workflow.split("- name: Run bounded shard", 1)[1].split(
        "- uses: actions/upload-artifact", 1
    )[0]
    assert 'FAIL_ON_ZERO_WORKING: "false"' in bounded_shard


def test_cli_delegates_availability_policy_to_pipeline(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    async def fake_run_full_pipeline(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            success=True,
            error=None,
            stats=SimpleNamespace(
                duration=0.1,
                fetched_lines=0,
                tested=0,
                working=0,
                geo_resolved=0,
                time_limited=False,
            ),
        )

    source_file = tmp_path / "sources.txt"
    source_file.write_text("https://example.invalid/source\n", encoding="utf-8")

    with (
        patch.object(cli, "run_full_pipeline", new=fake_run_full_pipeline),
        patch.object(cli, "DEFAULT_RESOLVER", new=None),
        patch.dict(os.environ, {}, clear=False),
    ):
        os.environ.pop("FAIL_ON_ZERO_WORKING", None)
        result = CliRunner().invoke(
            cli.main,
            [
                "merge",
                "--sources",
                str(source_file),
                "--output",
                str(tmp_path / "output"),
            ],
        )

    assert result.exit_code == 0, result.output
    assert captured["fail_on_zero_working"] is False
    assert "strict_security" not in captured
    assert "aggregate release validation" in result.output


def test_cli_strict_alias_enables_zero_working_policy(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    async def fake_run_full_pipeline(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            success=True,
            error=None,
            stats=SimpleNamespace(
                duration=0.1,
                fetched_lines=1,
                tested=1,
                working=1,
                geo_resolved=0,
                time_limited=False,
            ),
        )

    source_file = tmp_path / "sources.txt"
    source_file.write_text("https://example.invalid/source\n", encoding="utf-8")

    with (
        patch.object(cli, "run_full_pipeline", new=fake_run_full_pipeline),
        patch.object(cli, "DEFAULT_RESOLVER", new=None),
        patch.dict(os.environ, {}, clear=False),
    ):
        os.environ.pop("FAIL_ON_ZERO_WORKING", None)
        result = CliRunner().invoke(
            cli.main,
            [
                "merge",
                "--sources",
                str(source_file),
                "--output",
                str(tmp_path / "output"),
                "--strict",
            ],
        )

    assert result.exit_code == 0, result.output
    assert captured["fail_on_zero_working"] is True
''',
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
