# SPDX-License-Identifier: AGPL-3.0-or-later

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_local_tester_build_docs_include_strict_trust_pin() -> None:
    for relative in (
        "docs/wiki/project/getting_started.md",
        "docs/wiki/project/09-contributing.md",
        "docs/wiki/project/10-troubleshooting.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "configstream-tester.sha256" in text
        assert "Production-mode startup intentionally rejects an unpinned tester" in text or (
            "chmod 0444 configstream-tester.sha256" in text
        )


def test_architecture_never_claims_stego_secret_is_public_frontend_data() -> None:
    text = (ROOT / "docs/wiki/project/02-architecture.md").read_text(encoding="utf-8")

    assert "STEGO_KEY` (Fernet) is injected into the frontend JS" not in text
    assert "STEGO_KEY` is never published in frontend JavaScript" in text
    assert "public GitHub Pages bundle" in text
