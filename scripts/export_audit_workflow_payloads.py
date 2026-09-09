#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Build temporary ordinary-file copies of audited workflow edits.

This script exists only to transport exact workflow blobs through the Git data API.
The helper workflow and generated payload directory are removed in the promotion commit.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".audit-workflow-payload"


def build_main() -> str:
    path = ROOT / ".github/workflows/main.yml"
    text = path.read_text(encoding="utf-8")

    if "python -m configstream.cli update-databases --geoip-only" not in text:
        old = "python -m configstream.cli update-databases\n"
        if old not in text:
            raise RuntimeError("GeoIP update command changed unexpectedly")
        text = text.replace(
            old, "python -m configstream.cli update-databases --geoip-only\n", 1
        )

    setup_start = text.index("  setup_geoip:")
    setup_end = text.index("  setup_matrix:", setup_start)
    section = text[setup_start:setup_end]
    if "retention-days: 30" not in section:
        if "retention-days: 1" not in section:
            raise RuntimeError("GeoIP retention policy changed unexpectedly")
        section = section.replace("retention-days: 1", "retention-days: 30", 1)
    text = text[:setup_start] + section + text[setup_end:]

    start = text.index("      - name: Record artifact downloads\n")
    end = text.index("\n      - name:", start + 1)
    replacement = '''      - name: Record artifact downloads
        if: always()
        run: |
          set -euo pipefail
          shard_status="${{ steps.shard_download.outcome }}"
          if [ "$shard_status" = success ]; then
            if ! python - <<'PYCODE'
          import json
          from pathlib import Path

          matrix = json.loads(Path("matrix-artifact/source-matrix.json").read_text(encoding="utf-8"))
          expected = sum(1 for row in matrix.get("include", []) if row.get("enabled", True))
          lineage = list(Path("artifacts").rglob("shard_lineage.json"))
          if expected <= 0 or len(lineage) != expected:
              raise SystemExit(
                  f"shard artifact lineage mismatch: expected {expected}, found {len(lineage)}"
              )
          PYCODE
            then
              shard_status=failure
            fi
          fi
          python scripts/resilient_stage.py record --name shard-download --status "$shard_status"
          python scripts/resilient_stage.py record --name wasm-download --status "${{ steps.wasm_download.outcome }}"
          python scripts/resilient_stage.py record --name matrix-artifact-download --status "${{ steps.matrix_artifact_download.outcome }}"
'''
    text = text[:start] + replacement.rstrip("\n") + text[end:]
    return text


def build_pages() -> str:
    path = ROOT / ".github/workflows/deploy-pages.yml"
    text = path.read_text(encoding="utf-8")

    if "allow_bootstrap_without_lkg:" not in text:
        run_start = text.index("      run_id:\n")
        run_end = text.index("\n\n", run_start)
        addition = '''
      allow_bootstrap_without_lkg:
        description: Allow a manual first deployment when no verified rollback baseline exists
        required: false
        default: false
        type: boolean'''
        text = text[:run_end] + addition + text[run_end:]

    if 'echo "ROLLBACK_READY=false" >> "$GITHUB_ENV"' not in text:
        old = '          echo "HAS_LKG=false" >> "$GITHUB_ENV"\n'
        if old not in text:
            raise RuntimeError("Pages LKG initialization changed unexpectedly")
        text = text.replace(
            old,
            old + '          echo "ROLLBACK_READY=false" >> "$GITHUB_ENV"\n',
            1,
        )

    gate_name = "      - name: Require rollback baseline before production mutation\n"
    if gate_name not in text:
        marker = "      - name: Upload last-known-good rollback artifact\n"
        if marker not in text:
            raise RuntimeError("Pages rollback upload marker changed unexpectedly")
        gate = '''      - name: Require rollback baseline before production mutation
        if: always()
        env:
          ALLOW_BOOTSTRAP_WITHOUT_LKG: ${{ github.event_name == 'workflow_dispatch' && inputs.allow_bootstrap_without_lkg || false }}
        run: |
          set -euo pipefail
          if [ "${HAS_LKG:-false}" = true ]; then
            echo "ROLLBACK_READY=true" >> "$GITHUB_ENV"
            python scripts/resilient_stage.py record --name rollback-baseline --status success --report-dir deploy-evidence/stages --description "Verified last-known-good Pages release is available"
          elif [ "$ALLOW_BOOTSTRAP_WITHOUT_LKG" = true ]; then
            echo "ROLLBACK_READY=true" >> "$GITHUB_ENV"
            python scripts/resilient_stage.py record --name rollback-baseline --status success --report-dir deploy-evidence/stages --description "Explicit manual bootstrap approved without a rollback baseline"
          else
            echo "DEPLOY_READY=false" >> "$GITHUB_ENV"
            python scripts/resilient_stage.py record --name rollback-baseline --status failed --exit-code 1 --report-dir deploy-evidence/stages --description "Deployment blocked because no verified rollback baseline is available"
          fi
'''
        text = text.replace(marker, gate + marker, 1)

    upload_if = "        if: env.DEPLOY_READY == 'true'\n"
    hardened_upload_if = (
        "        if: env.DEPLOY_READY == 'true' && env.ROLLBACK_READY == 'true'\n"
    )
    if hardened_upload_if not in text:
        if upload_if not in text:
            raise RuntimeError("Pages artifact upload condition changed unexpectedly")
        text = text.replace(upload_if, hardened_upload_if, 1)

    deploy_if = (
        "        if: env.DEPLOY_READY == 'true' && "
        "steps.pages_artifact.outcome == 'success'\n"
    )
    hardened_deploy_if = (
        "        if: env.DEPLOY_READY == 'true' && env.ROLLBACK_READY == 'true' && "
        "steps.pages_artifact.outcome == 'success'\n"
    )
    if hardened_deploy_if not in text:
        if deploy_if not in text:
            raise RuntimeError("Pages deploy condition changed unexpectedly")
        text = text.replace(deploy_if, hardened_deploy_if, 1)

    required = "            --required-stage verify-sealed-pages-artifact \\\n"
    rollback_required = "            --required-stage rollback-baseline \\\n"
    if rollback_required not in text:
        if required not in text:
            raise RuntimeError("Pages readiness stage list changed unexpectedly")
        text = text.replace(required, required + rollback_required, 1)

    return text


def main() -> int:
    OUT.mkdir(exist_ok=True)
    payloads = {"main.yml": build_main(), "deploy-pages.yml": build_pages()}
    for name, content in payloads.items():
        yaml.safe_load(content)
        path = OUT / name
        path.write_text(content, encoding="utf-8")
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
