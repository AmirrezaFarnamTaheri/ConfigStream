# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path


def test_pages_workflow_snapshots_and_restores_last_known_good() -> None:
    workflow = Path(".github/workflows/deploy-pages.yml").read_text(encoding="utf-8")
    assert "Snapshot current verified Pages release" in workflow
    assert "scripts/snapshot_pages_release.py" in workflow
    assert "cryptography==49.0.0" in workflow
    assert "CS_PUBLIC_KEY: ${{ secrets.CS_PUBLIC_KEY }}" in workflow
    assert "PYTHONPATH: src" in workflow
    assert "Upload last-known-good rollback artifact" in workflow
    assert "Restore last-known-good Pages release" in workflow
    assert "Verify rollback restoration" in workflow
    assert "env.SMOKE_OK != 'true'" in workflow
    assert "last-known-good" in workflow
    assert "name: github-pages-candidate" in workflow
    assert "artifact_name: github-pages-candidate" in workflow
    assert "name: github-pages-last-known-good" in workflow
    assert "artifact_name: github-pages-last-known-good" in workflow
