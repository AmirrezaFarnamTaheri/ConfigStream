# SPDX-License-Identifier: AGPL-3.0-or-later
"""Temporary exact-byte transformer for release workflow hardening."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / ".ci-staging"
STAGING.mkdir(exist_ok=True)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def replace_first(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"{label}: expected at least one match, found 0")
    return text.replace(old, new, 1)


deploy = (ROOT / ".github/workflows/deploy-pages.yml").read_text(encoding="utf-8")
deploy = replace_once(
    deploy,
    "        env:\n"
    "          EXPECTED_SOURCE_SHA: ${{ steps.locate.outputs.source_head_sha }}\n"
    "        run: |\n",
    "        env:\n"
    "          EXPECTED_SOURCE_SHA: ${{ steps.locate.outputs.source_head_sha }}\n"
    "          CS_PUBLIC_KEY: ${{ secrets.CS_PUBLIC_KEY }}\n"
    "        run: |\n",
    "pre-deploy public-key binding",
)
deploy = replace_once(
    deploy,
    "              set -euo pipefail\n"
    "              before=$(find output -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -d\" \" -f1)\n",
    "              set -euo pipefail\n"
    "              if [ -z \"${CS_PUBLIC_KEY:-}\" ]; then\n"
    "                echo \"CS_PUBLIC_KEY must be configured for Pages artifact verification\" >&2\n"
    "                exit 1\n"
    "              fi\n"
    "              before=$(find output -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -d\" \" -f1)\n",
    "pre-deploy fail-closed signature check",
)
deploy = replace_once(
    deploy,
    "            if [ -n \"${CS_PUBLIC_KEY:-}\" ]; then\n"
    "              verify_args+=(--public-key \"$CS_PUBLIC_KEY\")\n"
    "            else\n"
    "              echo \"CS_PUBLIC_KEY is not configured; verifying deployment identity and integrity without signature validation\"\n"
    "            fi\n",
    "            if [ -z \"${CS_PUBLIC_KEY:-}\" ]; then\n"
    "              echo \"CS_PUBLIC_KEY must be configured for Pages deployment verification\" >&2\n"
    "              exit 1\n"
    "            fi\n"
    "            verify_args+=(--public-key \"$CS_PUBLIC_KEY\")\n",
    "post-deploy fail-closed signature check",
)
deploy = replace_once(
    deploy,
    "      - name: Verify rollback restoration\n"
    "        id: verify_rollback\n"
    "        if: always() && env.SMOKE_OK != 'true' && env.HAS_LKG == 'true' && steps.rollback_artifact.outcome == 'success'\n"
    "        continue-on-error: true\n"
    "        run: |\n",
    "      - name: Verify rollback restoration\n"
    "        id: verify_rollback\n"
    "        if: always() && env.SMOKE_OK != 'true' && env.HAS_LKG == 'true' && steps.rollback_artifact.outcome == 'success'\n"
    "        continue-on-error: true\n"
    "        env:\n"
    "          CS_PUBLIC_KEY: ${{ secrets.CS_PUBLIC_KEY }}\n"
    "        run: |\n",
    "rollback public-key binding",
)
deploy = replace_once(
    deploy,
    "          set -euo pipefail\n"
    "          page_url=\"${{ steps.rollback_deployment.outputs.page_url }}\"\n"
    "          if [ -z \"$page_url\" ]; then\n",
    "          set -euo pipefail\n"
    "          if [ -z \"${CS_PUBLIC_KEY:-}\" ]; then\n"
    "            echo \"CS_PUBLIC_KEY must be configured for Pages rollback verification\" >&2\n"
    "            exit 1\n"
    "          fi\n"
    "          page_url=\"${{ steps.rollback_deployment.outputs.page_url }}\"\n"
    "          if [ -z \"$page_url\" ]; then\n",
    "rollback fail-closed signature check",
)
deploy = replace_once(
    deploy,
    "            -- python scripts/verify_pages_deployment.py \"$page_url\" --report-file deploy-evidence/rollback-smoke-report.json\n",
    "            -- python scripts/verify_pages_deployment.py \"$page_url\" --public-key \"$CS_PUBLIC_KEY\" --report-file deploy-evidence/rollback-smoke-report.json\n",
    "rollback signature verification command",
)
if "without signature validation" in deploy:
    raise SystemExit("optional Pages signature fallback remains")
if deploy.count("CS_PUBLIC_KEY: ${{ secrets.CS_PUBLIC_KEY }}") < 4:
    raise SystemExit("expected public key at candidate, snapshot, deployed-candidate, and rollback boundaries")
(STAGING / "deploy-pages.yml").write_text(deploy, encoding="utf-8")

release = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
release = replace_first(
    release,
    "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7\n"
    "        with:\n"
    "          fetch-depth: 1\n"
    "          persist-credentials: false\n",
    "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7\n"
    "        with:\n"
    "          fetch-depth: 0\n"
    "          persist-credentials: false\n",
    "release verification full-history checkout",
)
release = replace_once(
    release,
    "      - name: Validate repository contracts and release state\n"
    "        run: |\n"
    "          set -euo pipefail\n"
    "          python scripts/verify_repository.py --profile static\n",
    "      - name: Validate repository contracts and release state\n"
    "        run: |\n"
    "          set -euo pipefail\n"
    "          git fetch --no-tags origin main:refs/remotes/origin/main\n"
    "          tag_commit=\"$(git rev-list -n 1 \"$GITHUB_REF_NAME\")\"\n"
    "          if [ -z \"$tag_commit\" ] || ! git merge-base --is-ancestor \"$tag_commit\" refs/remotes/origin/main; then\n"
    "            echo \"Release tag must point to a commit reachable from main\" >&2\n"
    "            exit 1\n"
    "          fi\n"
    "          python scripts/verify_repository.py --profile static\n",
    "tag main-history verification",
)
for token in (
    "fetch-depth: 0",
    "git fetch --no-tags origin main:refs/remotes/origin/main",
    'git rev-list -n 1 "$GITHUB_REF_NAME"',
    'git merge-base --is-ancestor "$tag_commit" refs/remotes/origin/main',
):
    if token not in release:
        raise SystemExit(f"missing release ancestry control: {token}")
(STAGING / "release.yml").write_text(release, encoding="utf-8")
