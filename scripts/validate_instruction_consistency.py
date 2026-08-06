# SPDX-License-Identifier: AGPL-3.0-or-later
"""Keep contributor instructions aligned with executable repository contracts."""

from __future__ import annotations

from pathlib import Path


def validate(root: Path) -> list[str]:
    root = Path(root)
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    gemini = (root / "GEMINI.md").read_text(encoding="utf-8")
    sources = (root / "sources" / "README.md").read_text(encoding="utf-8")
    errors: list[str] = []

    required_agents = (
        "`docs/readiness.json` is the canonical release checkpoint",
        "scripts/verify_repository.py --profile full",
        "src/configstream/pipeline/fetcher.py",
        "source admission and pinned-IP/Host/SNI",
        "`sources/batch_*.txt` are the authored operational source lists",
    )
    for token in required_agents:
        if token not in agents:
            errors.append(f"AGENTS.md missing current contract: {token}")

    required_gemini = (
        "Canonical Pipeline and Compatibility Shims",
        "Root `src/configstream/producer.py` and `src/configstream/consumer.py` remain thin compatibility shims",
        "Root `pipeline.py` and `fetcher.py` are absent",
        "`docs/readiness.json` and generated `STATUS.md` remain `CONDITIONAL`",
        "`sources/batch_*.txt` are the authored operational source lists",
    )
    for token in required_gemini:
        if token not in gemini:
            errors.append(f"GEMINI.md missing current contract: {token}")

    required_sources = (
        "17 batch files",
        "python scripts/deduplicate_sources.py",
        "source-admission.json",
    )
    for token in required_sources:
        if token not in sources:
            errors.append(f"sources/README.md missing current contract: {token}")

    stale = (
        "ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md",
        "docs/encyclopedia",
        "consolidated_sources.txt",
        "Legacy files `pipeline.py`, `fetcher.py`, `producer.py`, `consumer.py` have been removed",
        "src/configstream/fetcher.py",
    )
    combined = "\n".join((agents, gemini, sources))
    for token in stale:
        if token in combined:
            errors.append(f"stale instruction claim remains: {token}")
    return errors


def main() -> int:
    errors = validate(Path("."))
    if errors:
        print("ERROR: contributor instructions contradict repository reality")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("OK: contributor instructions match current executable contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
