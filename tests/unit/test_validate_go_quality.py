# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path
from scripts.validate_go_quality import validate

ROOT = Path(__file__).resolve().parents[2]


def test_native_go_quality_gates_are_present() -> None:
    assert validate(Path(".")) == []


def test_utls_client_cannot_disable_certificate_verification() -> None:
    source = (ROOT / "src/go/utls_client/main.go").read_text(encoding="utf-8")
    assert "skip-verify" not in source
    assert "InsecureSkipVerify" not in source
