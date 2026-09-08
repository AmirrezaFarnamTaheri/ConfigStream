# SPDX-License-Identifier: AGPL-3.0-or-later
"""Apply the locally verified audit remediation patch exactly once."""
from __future__ import annotations

import base64
from pathlib import Path
import subprocess
import tempfile
import zlib

CHUNKS = [Path(f"scripts/.audit_patch_{index:02d}") for index in range(4)]


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"expected remediation anchor missing in {path}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def apply_patch() -> None:
    encoded = "".join(path.read_text(encoding="ascii") for path in CHUNKS)
    payload = zlib.decompress(base64.b64decode(encoded))
    with tempfile.NamedTemporaryFile(suffix=".patch", delete=False) as handle:
        handle.write(payload)
        patch_path = Path(handle.name)
    try:
        subprocess.run(["git", "apply", "--check", str(patch_path)], check=True)
        subprocess.run(["git", "apply", str(patch_path)], check=True)
    finally:
        patch_path.unlink(missing_ok=True)


def patch_main_workflow() -> None:
    path = ".github/workflows/main.yml"
    replace_once(
        path,
        """            scripts/native_client_checks.py \\
            scripts/release_gate.py \\
            scripts/validate_workflows.py
""",
        """            scripts/native_client_checks.py \\
            scripts/release_gate.py \\
            scripts/validate_container_shells.py \\
            scripts/validate_workflows.py
""",
    )
    replace_once(
        path,
        """          python scripts/validate_workflows.py
          python scripts/verify_repository.py --profile static
""",
        """          python scripts/validate_workflows.py
          python scripts/validate_container_shells.py
          python scripts/verify_repository.py --profile static
""",
    )
    replace_once(
        path,
        """            tests/unit/test_validate_workflows.py \\
            tests/unit/test_validate_workflows_resilient.py \\
""",
        """            tests/unit/test_validate_workflows.py \\
            tests/unit/test_validate_workflows_resilient.py \\
            tests/unit/test_validate_container_shells.py \\
""",
    )
    replace_once(
        path,
        "python -m configstream.cli update-databases\n",
        "python -m configstream.cli update-databases --geoip-only\n",
    )
    replace_once(
        path,
        """          retention-days: 1
          overwrite: true

  setup_matrix:""",
        """          retention-days: 30
          overwrite: true

  setup_matrix:""",
    )
    replace_once(
        path,
        """      - name: Record artifact downloads
        if: always()
        run: |
          python scripts/resilient_stage.py record --name shard-download --status "${{ steps.shard_download.outcome }}"
          python scripts/resilient_stage.py record --name wasm-download --status "${{ steps.wasm_download.outcome }}"
          python scripts/resilient_stage.py record --name matrix-artifact-download --status "${{ steps.matrix_artifact_download.outcome }}"
""",
        """      - name: Record artifact downloads
        if: always()
        shell: bash
        run: |
          set -euo pipefail
          shard_status="${{ steps.shard_download.outcome }}"
          if [ "$shard_status" = success ]; then
            if python - <<'PY'
          import json
          from pathlib import Path

          matrix_path = Path("matrix-artifact/source-matrix.json")
          if not matrix_path.is_file():
              raise SystemExit("source matrix artifact is missing")
          payload = json.loads(matrix_path.read_text(encoding="utf-8"))
          rows = payload.get("include") if isinstance(payload, dict) else None
          if not isinstance(rows, list):
              raise SystemExit("source matrix artifact has no include list")
          expected = sum(
              1
              for row in rows
              if isinstance(row, dict) and row.get("enabled") is True
          )
          actual = len(list(Path("artifacts").rglob("shard_lineage.json")))
          if expected <= 0:
              raise SystemExit("source matrix contains no enabled shards")
          if actual != expected:
              raise SystemExit(
                  f"shard artifact lineage mismatch: expected={expected} actual={actual}"
              )
          print(f"Verified shard artifacts: expected={expected} actual={actual}")
          PY
            then
              shard_status=success
            else
              shard_status=failure
            fi
          fi
          python scripts/resilient_stage.py record --name shard-download --status "$shard_status" --description "action=${{ steps.shard_download.outcome }}; semantic shard lineage check"
          python scripts/resilient_stage.py record --name wasm-download --status "${{ steps.wasm_download.outcome }}"
          python scripts/resilient_stage.py record --name matrix-artifact-download --status "${{ steps.matrix_artifact_download.outcome }}"
""",
    )


def main() -> int:
    apply_patch()
    patch_main_workflow()
    subprocess.run(["python", "scripts/validate_workflows.py"], check=True)
    subprocess.run(["python", "scripts/validate_container_shells.py"], check=True)
    subprocess.run(
        [
            "python",
            "-m",
            "py_compile",
            "scripts/aggregate_shard_health.py",
            "scripts/resilient_stage.py",
            "src/configstream/cli.py",
            "src/configstream/lab_validation.py",
            "src/configstream/pipeline/fetcher.py",
            "src/configstream/pipeline/producer.py",
            "src/configstream/server/routes/lab.py",
            "src/configstream/tools/dns_scanner/python/dnsscanner_tui.py",
        ],
        check=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
