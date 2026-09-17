# SPDX-License-Identifier: AGPL-3.0-or-later
"""Temporary exact-byte transformer for canonical Pages source hardening."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / ".ci-staging"
STAGING.mkdir(exist_ok=True)
SOURCE = ROOT / ".github/workflows/deploy-pages.yml"
TARGET = STAGING / "deploy-pages.yml"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


text = SOURCE.read_text(encoding="utf-8")
text = replace_once(
    text,
    '    workflows: ["Config\'s Stream", "Retest"]\n',
    '    workflows: ["Config\'s Stream"]\n',
    "workflow_run canonical source",
)
text = replace_once(
    text,
    "          EVENT_NAME: ${{ github.event_name }}\n",
    "",
    "remove unused qualification event name",
)
text = replace_once(
    text,
    '          source_name=$(gh api "repos/${REPOSITORY}/actions/runs/${selected}" --jq \'.name\')\n',
    "",
    "remove Retest source-name probe",
)
text = replace_once(
    text,
    '          if [ "$EVENT_NAME" = workflow_run ] && [ "$source_name" = Retest ]; then\n'
    '            echo "has_candidate=false" >> "$GITHUB_OUTPUT"\n'
    '            echo "Retest run $selected completed successfully without pipeline-output; deployment is intentionally skipped." >> "$GITHUB_STEP_SUMMARY"\n'
    '            exit 0\n'
    '          fi\n\n',
    "",
    "remove Retest deployment bypass",
)
text = replace_once(
    text,
    '          allowed_workflows = {"Config\'s Stream", "Retest"}\n',
    '          allowed_workflows = {"Config\'s Stream"}\n',
    "runtime canonical source allowlist",
)

if "Retest" in text:
    raise SystemExit("Retest still appears in deploy-pages.yml after canonicalization")
if 'workflows: ["Config\'s Stream"]' not in text:
    raise SystemExit("canonical workflow_run trigger is missing")
if 'allowed_workflows = {"Config\'s Stream"}' not in text:
    raise SystemExit("canonical runtime source allowlist is missing")

TARGET.write_text(text, encoding="utf-8")
