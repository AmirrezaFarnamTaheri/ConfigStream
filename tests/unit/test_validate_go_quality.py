# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path

from scripts.validate_go_quality import _go_test_commands, _has_gate, validate

ROOT = Path(__file__).resolve().parents[2]


def test_native_go_quality_gates_are_present() -> None:
    assert validate(Path(".")) == []


def test_go_quality_parser_accepts_governed_linker_flag() -> None:
    commands = _go_test_commands("""
        go test -ldflags="-checklinkname=0" ./...
        go test -ldflags="-checklinkname=0" -race ./...
        go test -ldflags="-checklinkname=0" . -run=^$ -fuzz=FuzzParseConfig -fuzztime=5s
        go test . -run=^$ -fuzz=FuzzParseTarget -fuzztime=5s
        go test -ldflags="-checklinkname=0" . -run=^$ -bench=. -benchtime=1x
        """)

    assert _has_gate(commands, required=("./...",))
    assert _has_gate(commands, required=("-race", "./..."))
    assert _has_gate(commands, required=("-fuzz=FuzzParseConfig",))
    assert _has_gate(commands, required=("-fuzz=FuzzParseTarget",))
    assert _has_gate(commands, required=("-bench=.",))


def test_unit_gate_does_not_accept_only_race_or_fuzz() -> None:
    commands = _go_test_commands("""
        go test -race ./...
        go test . -run=^$ -fuzz=FuzzParseConfig -fuzztime=5s
        """)

    assert not _has_gate(
        commands,
        required=("./...",),
        forbidden_prefixes=("-race", "-fuzz=", "-bench="),
    )


def test_utls_client_cannot_disable_certificate_verification() -> None:
    source = (ROOT / "src/go/utls_client/main.go").read_text(encoding="utf-8")
    assert "skip-verify" not in source
    assert "InsecureSkipVerify" not in source
