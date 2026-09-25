# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from scripts import run_live_smoke

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "configstream-live-smoke.yml"
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "live_smoke_sources.txt"


def _run_args(tmp_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        sources=tmp_path / "sources.txt",
        output=tmp_path / "output",
        log=tmp_path / "smoke.log",
        selected_source=tmp_path / "selected.txt",
        max_workers=8,
        fetch_timeout=15,
        max_latency=6000,
        attempt_timeout=90,
    )


def _triggers(payload: dict) -> dict:
    value = payload.get("on")
    if value is None:
        value = payload.get(True, {})
    return value if isinstance(value, dict) else {}


def test_live_smoke_sources_are_bounded_https_and_admitted() -> None:
    candidates = run_live_smoke.load_candidates(FIXTURE)
    assert len(candidates) == 2
    admitted: set[str] = set()
    for path in sorted((REPO_ROOT / "sources").glob("batch_*.txt")):
        admitted.update(
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    assert set(candidates) <= admitted
    assert all(source.startswith("https://") for source in candidates)


def test_live_smoke_output_distinguishes_defects_from_missing_liveness(
    tmp_path: Path,
) -> None:
    output = tmp_path / "output"
    output.mkdir()
    state, _ = run_live_smoke.classify_output(output)
    assert state == "broken"

    (output / "proxies.json").write_text("[]\n", encoding="utf-8")
    (output / "metadata.json").write_text('{"final_count": 0}\n', encoding="utf-8")
    state, _ = run_live_smoke.classify_output(output)
    assert state == "broken"

    (output / "proxies.json").write_text(
        json.dumps([{"protocol": "socks4", "is_working": False}]) + "\n",
        encoding="utf-8",
    )
    (output / "metadata.json").write_text('{"final_count": 1}\n', encoding="utf-8")
    state, reason = run_live_smoke.classify_output(output)
    assert state == "no_live_proxies"
    assert "none are working" in reason

    (output / "proxies.json").write_text(
        json.dumps([{"protocol": "socks4", "is_working": True}]) + "\n",
        encoding="utf-8",
    )
    state, reason = run_live_smoke.classify_output(output)
    assert state == "working"
    assert "with 1 working" in reason


def test_live_smoke_rejects_malformed_proxy_entries(tmp_path: Path) -> None:
    """Malformed output is a generator defect, not an availability problem."""
    output = tmp_path / "output"
    output.mkdir()
    (output / "metadata.json").write_text('{"final_count": 1}\n', encoding="utf-8")

    for payload in (
        "[null]",
        '["not-a-proxy"]',
        "[1]",
        '[{"is_working": false}, null]',
    ):
        (output / "proxies.json").write_text(payload + "\n", encoding="utf-8")
        state, reason = run_live_smoke.classify_output(output)
        assert state == "broken", payload
        assert "malformed" in reason


def test_live_smoke_falls_back_to_second_candidate(tmp_path: Path, monkeypatch) -> None:
    sources = tmp_path / "sources.txt"
    sources.write_text(
        "https://example.test/one\nhttps://example.test/two\n", encoding="utf-8"
    )
    output = tmp_path / "output"
    log = tmp_path / "smoke.log"
    selected = tmp_path / "selected.txt"
    attempts: list[str] = []

    def fake_attempt(**kwargs):
        source = str(kwargs["source"])
        attempts.append(source)
        target = Path(kwargs["output_dir"])
        target.mkdir(parents=True, exist_ok=True)
        if source.endswith("/one"):
            (target / "proxies.json").write_text(
                json.dumps([{"protocol": "socks4", "is_working": False}]) + "\n",
                encoding="utf-8",
            )
            (target / "metadata.json").write_text(
                '{"final_count": 1}\n', encoding="utf-8"
            )
            return 0, "first produced only non-working output\n"
        (target / "proxies.json").write_text(
            json.dumps([{"protocol": "socks4", "is_working": True}]) + "\n",
            encoding="utf-8",
        )
        (target / "metadata.json").write_text('{"final_count": 1}\n', encoding="utf-8")
        return 0, "second succeeded\n"

    monkeypatch.setattr(run_live_smoke, "_run_attempt", fake_attempt)
    args = argparse.Namespace(
        sources=sources,
        output=output,
        log=log,
        selected_source=selected,
        max_workers=8,
        fetch_timeout=15,
        max_latency=6000,
        attempt_timeout=90,
    )
    assert run_live_smoke.run(args) == 0
    assert attempts == ["https://example.test/one", "https://example.test/two"]
    assert selected.read_text(encoding="utf-8").strip().endswith("/two")
    assert "first produced only non-working output" in log.read_text(encoding="utf-8")


def test_live_smoke_succeeds_when_all_sources_have_no_live_proxies(
    tmp_path: Path, monkeypatch
) -> None:
    args = _run_args(tmp_path)
    args.sources.write_text(
        "https://example.test/one\nhttps://example.test/two\n", encoding="utf-8"
    )
    attempts: list[str] = []

    def fake_attempt(**kwargs):
        source = str(kwargs["source"])
        attempts.append(source)
        target = Path(kwargs["output_dir"])
        target.mkdir(parents=True, exist_ok=True)
        (target / "proxies.json").write_text(
            json.dumps([{"protocol": "socks4", "is_working": False}]) + "\n",
            encoding="utf-8",
        )
        (target / "metadata.json").write_text('{"final_count": 1}\n', encoding="utf-8")
        return 0, "completed without a working proxy\n"

    monkeypatch.setattr(run_live_smoke, "_run_attempt", fake_attempt)

    assert run_live_smoke.run(args) == 0
    assert attempts == ["https://example.test/one", "https://example.test/two"]
    assert not args.selected_source.exists()


def test_live_smoke_fails_when_a_source_produces_broken_output(
    tmp_path: Path, monkeypatch
) -> None:
    args = _run_args(tmp_path)
    args.sources.write_text("https://example.test/one\n", encoding="utf-8")

    def fake_attempt(**kwargs):
        target = Path(kwargs["output_dir"])
        target.mkdir(parents=True, exist_ok=True)
        (target / "proxies.json").write_text("not-json\n", encoding="utf-8")
        (target / "metadata.json").write_text('{"final_count": 1}\n', encoding="utf-8")
        return 0, "invalid output\n"

    monkeypatch.setattr(run_live_smoke, "_run_attempt", fake_attempt)

    assert run_live_smoke.run(args) == 1
    assert not args.selected_source.exists()


def test_live_smoke_workflow_is_read_only_bounded_and_full_path() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    payload = yaml.safe_load(text)
    triggers = _triggers(payload)
    assert "pull_request" in triggers
    assert "push" in triggers
    assert "workflow_dispatch" in triggers
    assert "secrets." not in text

    job = payload["jobs"]["live_full_path_smoke"]
    assert int(job["timeout-minutes"]) <= 8
    assert payload["permissions"] == {"contents": "read"}
    assert payload["env"]["ALLOW_ACTIVE_SCANNING"] == "false"
    assert payload["env"]["FORCE_SCANNER"] == "false"
    assert payload["env"]["MAX_LINES_PER_SOURCE"] == "16"
    assert payload["env"]["MAX_WORKERS"] == "8"
    assert payload["env"]["MIN_SOURCE_COVERAGE"] == "0.70"

    steps = [step for step in job.get("steps", []) if isinstance(step, dict)]
    uses = "\n".join(str(step.get("uses", "")) for step in steps)
    commands = "\n".join(str(step.get("run", "")) for step in steps)

    assert "actions/setup-go@" in uses
    assert "requirements-prod.txt" in commands
    assert "requirements-dev.txt" not in commands
    assert "CGO_ENABLED=0 go build" in commands
    assert "CONFIGSTREAM_TESTER_BIN=" in commands
    assert "python scripts/run_live_smoke.py" in commands
    assert "--max-workers 8" in commands
    assert "--attempt-timeout 90" in commands
    assert "python scripts/prepare_public_candidate.py" in commands
    assert "python scripts/finalize_release_outputs.py" in commands
    assert '--min-source-coverage "$MIN_SOURCE_COVERAGE"' in commands
    assert (
        "python scripts/validate_pages_artifact.py --refresh-contract smoke-public"
        in commands
    )

    live_step = next(step for step in steps if step.get("id") == "live_merge")
    assert live_step["continue-on-error"] is True

    public_step = next(
        step
        for step in steps
        if step.get("name") == "Exercise production public-output path"
    )
    assert public_step["if"] == "steps.live_merge.outcome == 'success'"

    report_step = next(
        step for step in steps if step.get("name") == "Report live smoke result"
    )
    assert "LIVE_PROBE_OUTCOME" in report_step.get("env", {})
    assert "live-smoke-status.json" in str(report_step.get("run", ""))
    assert "verified_working_proxies" in str(report_step.get("run", ""))

    enforce_step = next(
        step
        for step in steps
        if step.get("name")
        == "Enforce live production-path status on main and manual runs"
    )
    enforce_if = str(enforce_step["if"])
    assert "github.event_name != 'pull_request'" in enforce_if
    assert "steps.live_merge.outcome != 'success'" in enforce_if
    assert "production path" in str(enforce_step.get("run", ""))
    assert "exit 1" in str(enforce_step.get("run", ""))

    report_run = str(report_step.get("run", ""))
    assert "path_verified" in report_run
    assert "NO LIVE PROXIES (diagnostic only)" in report_run

    # The production public-output step must be addressable so the status
    # artifact cannot claim the full path passed when that step failed.
    assert public_step.get("id") == "public_output"
    report_env = report_step.get("env", {})
    assert "LIVE_PROBE_OUTCOME" in report_env
    assert "steps.public_output.outcome" in str(
        report_env.get("LIVE_PUBLIC_OUTPUT_OUTCOME")
    )
    assert "public_output_outcome == 'success'" in report_run
    # Enforcement must fail on either step, not just the merge probe.
    assert "steps.public_output.outcome != 'success'" in enforce_if

    upload_step = next(
        step for step in steps if step.get("name") == "Upload live smoke diagnostics"
    )
    assert "live-smoke-status.json" in str(upload_step["with"]["path"])
