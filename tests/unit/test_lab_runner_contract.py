# SPDX-License-Identifier: AGPL-3.0-or-later
"""Static safety contract for tools/lab-runner.sh."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "lab-runner.sh"


def test_lab_runner_never_interpolates_user_host_into_bash_code() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert 'bash -c \'exec 3<>"/dev/tcp/$1/$2"\' _ "$host" "$port"' in text
    assert 'bash -c "echo >/dev/tcp/$host/$port"' not in text
    assert "parse_hostport" in text
    assert "validate_port" in text


def test_lab_runner_has_child_cleanup_and_bounded_timeout_resolution() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "trap cleanup_child EXIT" in text
    assert "trap 'cleanup_child; exit 130' INT" in text
    assert "trap 'cleanup_child; exit 143' TERM" in text
    assert "command -v timeout" in text
    assert "command -v gtimeout" in text


def test_lab_runner_does_not_claim_nonfunctional_proxy_scanning() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "--through is not supported for raw TCP reachability scans" in text
    assert "scan-ips [--through proxy]" not in text
    assert 'PROXY_ARG="-x $2"' not in text


def test_lab_runner_requires_bracketed_ipv6_hostport_form() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "[IPv6]:port" in text
    assert "PARSED_HOST" in text
    assert "PARSED_PORT" in text
