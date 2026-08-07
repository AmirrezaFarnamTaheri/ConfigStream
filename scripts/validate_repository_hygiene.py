# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reject local process debris, redundant mirrors, and source-layout drift."""

from __future__ import annotations

from pathlib import Path

FORBIDDEN_PATHS = (
    "MagicMock",
    ".absolute-work",
    ".absolute.config.json",
    "ConfigStream_Executive_Assessment.md",
    "ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md",
    "consolidated_sources.txt",
    "docs/FRONTEND_ANALYTICS_GLOBE_AUDIT.md",
    "docs/encyclopedia",
    "docs/superpowers/plans",
    ".github/workflows/remediation-ci.yml",
    "review-stage",
    "repo-topology-out",
    "patch_schema.py",
    "patch_testers_init.py",
    "tools/scripts/ufw.sh",
    ".pylintrc",
    "scripts/generate_topology_viz.py",
    "scripts/repo_topology.py",
    "scripts/probe_external_verification.py",
    "scripts/frontend_verification",
    "scripts/generate_project_graph.py",
    "docs/project_tree_graph.html",
    "scripts/minify_frontend.py",
    "scripts/profile_performance.py",
    "scripts/take_deployment_screenshots.py",
    "scripts/generate_favicons.py",
    "scripts/security_audit.sh",
    "scripts/run_cycle.sh",
)
EXPECTED_BATCH_COUNT = 17
FORBIDDEN_FONT_SUFFIXES = {".eot", ".otf", ".ttf", ".woff", ".woff2"}
TOP_LEVEL_REVIEW_TOKENS = (
    "AUDIT",
    "REPORT",
    "PLAN",
    "SPEC",
    "DESLOP",
    "DEEPDIVE",
    "BLAST_RADIUS",
)
TOP_LEVEL_DOC_ALLOWLIST = {
    "README.md",
    "CENSORSHIP_EVASION.md",
    "CONFIG_FORGE.md",
    "DEBT_MATRIX.md",
    "DEPLOYMENT.md",
    "MODULE_OWNERSHIP.md",
    "client_format_contracts.md",
}


def _url_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def validate_source_layout(root: Path) -> list[str]:
    root = Path(root)
    source_dir = root / "sources"
    batch_files = sorted(source_dir.glob("batch_*.txt"))
    errors: list[str] = []

    if len(batch_files) != EXPECTED_BATCH_COUNT:
        errors.append(
            f"expected {EXPECTED_BATCH_COUNT} canonical source batches, found {len(batch_files)}"
        )

    owner_by_url: dict[str, Path] = {}
    for batch_file in batch_files:
        for url in _url_lines(batch_file):
            previous = owner_by_url.get(url)
            if previous is not None:
                errors.append(
                    f"duplicate source URL in {previous.relative_to(root)} and "
                    f"{batch_file.relative_to(root)}: {url}"
                )
            else:
                owner_by_url[url] = batch_file

    return errors


def _stale_top_level_review_docs(root: Path) -> list[str]:
    docs = root / "docs"
    if not docs.exists():
        return []
    return [
        path.relative_to(root).as_posix()
        for path in sorted(docs.glob("*.md"))
        if path.name not in TOP_LEVEL_DOC_ALLOWLIST
        and any(token in path.stem for token in TOP_LEVEL_REVIEW_TOKENS)
    ]


def validate(root: Path) -> list[str]:
    root = Path(root)
    errors = [
        f"generated, redundant, or one-off artifact present: {path}"
        for path in FORBIDDEN_PATHS
        if (root / path).exists()
    ]
    errors.extend(validate_source_layout(root))
    font_files = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in FORBIDDEN_FONT_SUFFIXES
    ]
    if font_files:
        errors.append(
            "binary font assets are not part of the source distribution; use system font stacks: "
            + ", ".join(sorted(font_files))
        )
    stale_docs = _stale_top_level_review_docs(root)
    if stale_docs:
        errors.append(
            "point-in-time review artifacts must live under dated docs/audits directories: "
            + ", ".join(stale_docs)
        )
    return errors


def main() -> int:
    errors = validate(Path("."))
    if errors:
        print("ERROR: repository hygiene validation failed")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("OK: repository hygiene and canonical source layout are clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
