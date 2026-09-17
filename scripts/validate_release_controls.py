# SPDX-License-Identifier: AGPL-3.0-or-later
"""Ratchet the release controls that must never be weakened."""

from __future__ import annotations
from pathlib import Path


def validate(root: Path) -> list[str]:
    root = Path(root)
    errors: list[str] = []
    workflow = (root / ".github/workflows/main.yml").read_text(encoding="utf-8")
    required_commands = (
        "scripts/prepare_public_candidate.py output output",
        "scripts/native_client_checks.py output",
        "scripts/release_gate.py output",
        "--native-report pipeline-evidence/native_client_check_report.json",
        "--promote",
    )
    for command in required_commands:
        if command not in workflow:
            errors.append(f"main workflow missing release control: {command}")
    positions = [workflow.find(command) for command in required_commands[:3]]
    if all(position >= 0 for position in positions) and positions != sorted(positions):
        errors.append(
            "release controls must run candidate preparation -> native checks -> release gate"
        )

    native = (root / "scripts/native_client_checks.py").read_text(encoding="utf-8")
    for target in ("sing-box", "mihomo", "xray"):
        if f'"{target}"' not in native:
            errors.append(f"native client checks missing required target: {target}")
    if 'summary["failed"] or summary["skipped"] or not checks' not in native:
        errors.append(
            "native client checks must fail on failed, skipped, or empty evidence"
        )

    gate = (root / "scripts/release_gate.py").read_text(encoding="utf-8")
    for target, artifact in (
        ("sing-box", "singbox.json"),
        ("mihomo", "clash.yaml"),
        ("xray", "xray.json"),
    ):
        if f'"{target}": "{artifact}"' not in gate:
            errors.append(
                f"release gate missing native requirement {target}:{artifact}"
            )
    if "def promote(" not in gate and "--promote" not in gate:
        errors.append("release gate has no promotion path")

    deploy = (root / ".github/workflows/deploy-pages.yml").read_text(encoding="utf-8")
    snapshot_controls = (
        "python scripts/snapshot_pages_release.py",
        "last-known-good",
        "HAS_LKG=true",
    )
    for control in snapshot_controls:
        if control not in deploy:
            errors.append(
                f"Pages deployment missing last-known-good snapshot control: {control}"
            )

    rollback_controls = (
        "Upload last-known-good rollback artifact",
        "Restore last-known-good Pages release",
        "steps.rollback_artifact.outcome == 'success'",
        "verify-rollback",
        "rollback-smoke-report.json",
    )
    for control in rollback_controls:
        if control not in deploy:
            errors.append(
                f"Pages deployment missing rollback restoration control: {control}"
            )

    public_key_binding = "CS_PUBLIC_KEY: ${{ secrets.CS_PUBLIC_KEY }}"
    if deploy.count(public_key_binding) < 3:
        errors.append(
            "Pages deployment must bind CS_PUBLIC_KEY at pre-deploy, rollback-snapshot, and post-deploy verification boundaries"
        )
    pages_signature_controls = (
        "CS_PUBLIC_KEY must be configured for Pages artifact verification",
        "CS_PUBLIC_KEY must be configured for Pages deployment verification",
        'verify_args+=(--public-key "$CS_PUBLIC_KEY")',
    )
    for control in pages_signature_controls:
        if control not in deploy:
            errors.append(
                f"Pages deployment missing fail-closed signature verification control: {control}"
            )
    if "without signature validation" in deploy:
        errors.append(
            "Pages deployment must not fall back to unsigned production verification"
        )

    release = (root / ".github/workflows/release.yml").read_text(encoding="utf-8")
    release_provenance_controls = (
        "fetch-depth: 0",
        "git fetch --no-tags origin main:refs/remotes/origin/main",
        'git rev-list -n 1 "$GITHUB_REF_NAME"',
        'git merge-base --is-ancestor "$tag_commit" refs/remotes/origin/main',
        "Release tag must point to a commit reachable from main",
    )
    for control in release_provenance_controls:
        if control not in release:
            errors.append(
                f"tagged release missing main-history provenance control: {control}"
            )

    frontend = (root / "frontend/assets/js/artifact-state.js").read_text(
        encoding="utf-8"
    )
    for token in (
        "canDistribute: false",
        "Distribution disabled:",
        "event.preventDefault()",
    ):
        if token not in frontend:
            errors.append(f"frontend distribution guard missing: {token}")
    return errors


def main() -> int:
    errors = validate(Path("."))
    if errors:
        print("ERROR: mandatory release controls were weakened")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(
        "OK: native validation, signed deployment, main-history provenance, rollback, and frontend fail-closed controls are intact"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
