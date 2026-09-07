# SPDX-License-Identifier: AGPL-3.0-or-later
"""Static safety contract for the privileged UFW helper."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "setup_firewall.sh"


def test_firewall_script_has_executable_fail_closed_preamble() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    lines = text.splitlines()

    assert lines[0] == "#!/usr/bin/env bash"
    assert "set -Eeuo pipefail" in text
    assert "if ! ufw --force enable" in text


def test_firewall_script_does_not_auto_open_bound_only_listeners() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "is_wildcard_listener" in text
    assert "skipped_bound_listeners" in text
    assert "Interface/loopback-bound listeners are not auto-opened." in text


def test_firewall_script_preserves_effective_or_current_ssh_port() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "SSH_CONNECTION" in text
    assert "sshd -T" in text
    assert "refusing to prepare UFW rules that could lock out remote access" in text
