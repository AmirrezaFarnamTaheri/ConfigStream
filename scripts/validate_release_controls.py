# SPDX-License-Identifier: AGPL-3.0-or-later
"""Ratchet the release controls that must never be weakened."""

from __future__ import annotations

import json
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
    # The exit contract stays fail-closed: empty evidence and skipped checks must
    # still fail, and every check must be routed through the shared blocking
    # policy rather than a blanket pass/fail on the summary counters.
    for control in (
        "def _blocks_release(",
        "connectivity_check_blocks_release",
        'if report["blocking_failures"]:',
        "return 1",
        "return 0 if checks else 1",
    ):
        if control not in native:
            errors.append(
                f"native client checks missing fail-closed release control: {control}"
            )
    if 'skipped = summary["skipped"]' not in native or "if skipped:" not in native:
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

    # Pages may consume only the canonical production pipeline. Retest rewrites
    # output contracts but does not execute the release-gate/native/promotion
    # sequence above, so it must never be a production deployment source.
    if 'workflows: ["Config\'s Stream"]' not in deploy:
        errors.append(
            "Pages workflow_run trigger must listen only to the canonical Config's Stream workflow"
        )
    if 'allowed_workflows = {"Config\'s Stream"}' not in deploy:
        errors.append(
            "Pages source allowlist must contain only the canonical Config's Stream workflow"
        )
    if 'workflows: ["Config\'s Stream", "Retest"]' in deploy or (
        'allowed_workflows = {"Config\'s Stream", "Retest"}' in deploy
    ):
        errors.append("Retest must not be eligible as a Pages deployment source")
    if 'source_name" = Retest' in deploy:
        errors.append(
            "Pages deployment must not carry a Retest-specific publication bypass"
        )

    snapshot_controls = (
        "python scripts/snapshot_pages_release.py",
        "last-known-good",
        "HAS_LKG=true",
        "snapshot_args+=(--allow-unsigned)",
        'payload.get("failure_kind") == "missing_manifest"',
        "Automatic first-deployment bootstrap approved",
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
        "steps.deployment.outcome == 'success' || steps.deployment.outcome == 'failure'",
        "verify-rollback",
        "rollback-smoke-report.json",
    )
    for control in rollback_controls:
        if control not in deploy:
            errors.append(
                f"Pages deployment missing rollback restoration control: {control}"
            )

    public_key_binding = "CS_PUBLIC_KEY: ${{ secrets.CS_PUBLIC_KEY }}"
    if deploy.count(public_key_binding) < 4:
        errors.append(
            "Pages deployment must bind CS_PUBLIC_KEY at candidate, rollback-snapshot, deployed-candidate, and restored-rollback verification boundaries"
        )

    unsigned_policy_binding = (
        "VARIABLE_ALLOW_UNSIGNED_PAGES: ${{ vars.ALLOW_UNSIGNED_PAGES }}"
    )
    if unsigned_policy_binding not in deploy:
        errors.append(
            "Pages deployment must expose the repository variable to the trust-policy resolver"
        )
    for control in (
        "Resolve Pages unsigned trust policy",
        "python scripts/pages_trust_policy.py",
        'echo "ALLOW_UNSIGNED_PAGES=$resolved" >> "$GITHUB_ENV"',
    ):
        if control not in deploy:
            errors.append(
                f"Pages deployment missing repository-bound unsigned policy control: {control}"
            )

    pipeline = (root / ".github/workflows/main.yml").read_text(encoding="utf-8")
    if "Resolve Pages unsigned trust policy" not in pipeline or (
        "python scripts/pages_trust_policy.py" not in pipeline
    ):
        errors.append(
            "Artifact generation must resolve the same Pages unsigned trust policy before frontend generation"
        )

    policy_path = root / "config/pages-trust-policy.json"
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Pages trust policy is unreadable: {exc}")
    else:
        if policy.get("schema_version") != 1:
            errors.append("Pages trust policy schema_version must be 1")
        repository = policy.get("repository")
        if not isinstance(repository, str) or not repository.strip():
            errors.append("Pages trust policy must bind a non-empty repository")
        if not isinstance(policy.get("allow_unsigned_pages"), bool):
            errors.append("Pages trust policy allow_unsigned_pages must be boolean")

    if deploy.count("validate_pages_signature_policy.py output") < 2:
        errors.append(
            "Pages candidate signature policy must run before deployment and again before post-deploy verification"
        )
    if deploy.count("validate_pages_signature_policy.py last-known-good") < 2:
        errors.append(
            "Pages rollback signature policy must run when snapshotting and when verifying restoration"
        )
    if 'signature_policy_args+=(--public-key "$CS_PUBLIC_KEY")' not in deploy:
        errors.append(
            "signed Pages policy validation must receive the configured public key explicitly"
        )
    if "signature_policy_args+=(--allow-unsigned)" not in deploy:
        errors.append(
            "unsigned Pages publication must require an explicit policy argument"
        )
    if deploy.count("verify_args+=(--allow-unsigned)") < 2:
        errors.append(
            "explicit unsigned Pages policy must reach candidate and rollback live smoke verification"
        )
    if 'verify_args+=(--public-key "$CS_PUBLIC_KEY")' not in deploy:
        errors.append(
            "signed Pages deployment must pass the configured public key to smoke verification"
        )
    if "without signature validation" in deploy:
        errors.append(
            "Pages deployment must not use an implicit missing-key unsigned fallback"
        )

    freshness_controls = (
        "Require source run to remain current main before publication",
        "gh api \"repos/${REPOSITORY}/branches/main\" --jq '.commit.sha'",
        "EXPECTED_SOURCE_SHA: ${{ steps.locate.outputs.source_head_sha }}",
        "--name source-freshness",
        "--required-stage source-freshness",
        "Authenticated source revision is still current main",
    )
    for control in freshness_controls:
        if control not in deploy:
            errors.append(
                f"Pages deployment missing source freshness control: {control}"
            )
    freshness_position = deploy.find(
        "Require source run to remain current main before publication"
    )
    candidate_upload_position = deploy.find("Upload sealed Pages artifact")
    if (
        freshness_position < 0
        or candidate_upload_position < 0
        or freshness_position > candidate_upload_position
    ):
        errors.append(
            "Pages source freshness must be checked before the candidate can be uploaded or deployed"
        )

    signature_policy = (root / "scripts/validate_pages_signature_policy.py").read_text(
        encoding="utf-8"
    )
    for control in (
        "--allow-unsigned",
        "--public-key",
        "signed artifacts must never be accepted without a trust anchor",
        "unsigned Pages publication is disabled by default",
        "configured Pages public key is not a valid Ed25519 public key",
        "Signer.verify_manifest_signature",
    ):
        if control not in signature_policy:
            errors.append(
                f"Pages signature policy missing fail-closed control: {control}"
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
        "OK: canonical source, native validation, explicit Pages signature policy, current-main freshness, main-history provenance, rollback, and frontend fail-closed controls are intact"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
