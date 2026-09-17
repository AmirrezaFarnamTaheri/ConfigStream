# SPDX-License-Identifier: AGPL-3.0-or-later
"""Temporary exact-byte transformer for final Pages freshness controls."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / ".ci-staging"
STAGING.mkdir(exist_ok=True)
source = ROOT / ".github/workflows/deploy-pages.yml"
target = STAGING / "deploy-pages.yml"
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    text = text.replace(old, new, 1)


anchor = (
    "      - name: Upload sealed Pages artifact\n"
    "        id: pages_artifact\n"
)
freshness = (
    "      - name: Require source to remain current main before publication\n"
    "        if: env.DEPLOY_READY == 'true' && env.ROLLBACK_READY == 'true'\n"
    "        env:\n"
    "          GH_TOKEN: ${{ github.token }}\n"
    "          SOURCE_SHA: ${{ steps.locate.outputs.source_head_sha }}\n"
    "        run: |\n"
    "          set -euo pipefail\n"
    "          current_main=$(gh api \\\n"
    "            -H 'Accept: application/vnd.github+json' \\\n"
    "            \"/repos/${GITHUB_REPOSITORY}/git/ref/heads/main\" \\\n"
    "            --jq '.object.sha')\n"
    "          if [ -z \"${SOURCE_SHA:-}\" ] || [ \"$SOURCE_SHA\" != \"$current_main\" ]; then\n"
    "            python scripts/resilient_stage.py record \\\n"
    "              --name current-main-source \\\n"
    "              --status failed \\\n"
    "              --exit-code 1 \\\n"
    "              --report-dir deploy-evidence/stages \\\n"
    "              --description \"Refusing stale Pages candidate: source=$SOURCE_SHA current-main=$current_main\"\n"
    "            echo \"::error::Refusing stale Pages deployment: source $SOURCE_SHA is not current main $current_main\"\n"
    "            exit 1\n"
    "          fi\n"
    "          python scripts/resilient_stage.py record \\\n"
    "            --name current-main-source \\\n"
    "            --status success \\\n"
    "            --report-dir deploy-evidence/stages \\\n"
    "            --description \"Pages candidate is bound to current main $current_main\"\n"
)
replace_once(anchor, freshness + anchor, "pre-publication current-main gate")

old_rollback = (
    "        if: always() && env.SMOKE_OK != 'true' && env.HAS_LKG == 'true' && steps.rollback_artifact.outcome == 'success'\n"
)
new_rollback = (
    "        if: always() && env.SMOKE_OK != 'true' && env.HAS_LKG == 'true' && steps.rollback_artifact.outcome == 'success' && steps.deployment.outcome != 'skipped'\n"
)
replace_once(old_rollback, new_rollback, "rollback only after deployment attempt")

for token in (
    "Require source to remain current main before publication",
    "/git/ref/heads/main",
    'SOURCE_SHA: ${{ steps.locate.outputs.source_head_sha }}',
    'steps.deployment.outcome != \'skipped\'',
):
    if token not in text:
        raise SystemExit(f"missing Pages freshness control: {token}")

target.write_text(text, encoding="utf-8")
