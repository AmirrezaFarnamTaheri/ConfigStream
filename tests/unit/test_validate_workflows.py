# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for workflow YAML validation."""

from __future__ import annotations

from pathlib import Path

from scripts import validate_workflows


def test_validate_workflows_accepts_current_repo_workflows() -> None:
    assert validate_workflows.main() == 0


def test_validate_workflows_reports_yaml_errors(tmp_path: Path, monkeypatch) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "broken.yml").write_text(
        "name: Broken\non: [push\njobs: {}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validate_workflows, "WORKFLOW_DIR", workflow_dir)

    assert validate_workflows.main() == 1


def test_validate_workflows_requires_pages_frontend_placeholder_guard(
    tmp_path: Path, monkeypatch
) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "deploy-pages.yml").write_text(
        """
name: Deploy
on:
  workflow_dispatch:
concurrency:
  group: pages
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - run: echo deploy
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(validate_workflows, "WORKFLOW_DIR", workflow_dir)

    assert validate_workflows.main() == 1


def test_validate_workflows_rejects_pages_frontend_dist_deploy(
    tmp_path: Path, monkeypatch
) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "deploy-pages.yml").write_text(
        """
name: Deploy
on:
  workflow_dispatch:
concurrency:
  group: pages
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - run: |
          npm run build
          cp -R frontend-dist/. output/
          python scripts/validate_frontend_placeholders.py --inject-env --strict output
        env:
          CS_PUBLIC_KEY: ${{ secrets.CS_PUBLIC_KEY }}
          STEGO_KEY: ${{ secrets.STEGO_KEY }}
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(validate_workflows, "WORKFLOW_DIR", workflow_dir)

    assert validate_workflows.main() == 1


def test_validate_workflows_requires_pages_public_smoke(
    tmp_path: Path, monkeypatch
) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "deploy-pages.yml").write_text(
        """
name: Deploy
on:
  workflow_dispatch:
concurrency:
  group: pages
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - run: |
          cp -R frontend/. output/
          python scripts/validate_frontend_placeholders.py --inject-env --strict output
        env:
          CS_PUBLIC_KEY: ${{ secrets.CS_PUBLIC_KEY }}
          STEGO_KEY: ${{ secrets.STEGO_KEY }}
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(validate_workflows, "WORKFLOW_DIR", workflow_dir)

    assert validate_workflows.main() == 1


def test_validate_workflows_requires_ci_frontend_browser_profile(
    tmp_path: Path, monkeypatch
) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text(
        """
name: CI
on:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -q
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(validate_workflows, "WORKFLOW_DIR", workflow_dir)

    assert validate_workflows.main() == 1


def test_validate_workflows_requires_frontend_smoke_node_browser(
    tmp_path: Path, monkeypatch
) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text(
        """
name: CI
on:
  pull_request:
jobs:
  frontend:
    runs-on: ubuntu-latest
    steps:
      - run: |
          npm ci
          npm run build
          npm run test:frontend:no-network
  frontend-browser:
    runs-on: ubuntu-latest
    steps:
      - run: |
          python -m playwright install --with-deps chromium
          npx playwright install chromium
          npm run test:frontend:browser
      - run: |
          python scripts/validate_capability_registry.py
          python scripts/validate_core_compatibility.py
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(validate_workflows, "WORKFLOW_DIR", workflow_dir)

    assert validate_workflows.main() == 1


def test_validate_workflows_requires_ci_capability_contract_validators(
    tmp_path: Path, monkeypatch
) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text(
        """
name: CI
on:
  pull_request:
jobs:
  frontend-browser:
    runs-on: ubuntu-latest
    steps:
      - run: |
          python -m playwright install --with-deps chromium
          npx playwright install chromium
          npm run test:frontend:browser
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(validate_workflows, "WORKFLOW_DIR", workflow_dir)

    assert validate_workflows.main() == 1


def test_validate_workflows_requires_release_capability_contract_validators(
    tmp_path: Path, monkeypatch
) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "release.yml").write_text(
        """
name: Release
on:
  workflow_dispatch:
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - run: python scripts/validate_versions.py
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(validate_workflows, "WORKFLOW_DIR", workflow_dir)

    assert validate_workflows.main() == 1


def test_validate_workflows_rejects_secret_context_in_if(
    tmp_path: Path, monkeypatch
) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "deploy_mirror.yml").write_text(
        """
name: Mirror
on:
  workflow_dispatch:
concurrency:
  group: mirror
jobs:
  mirror:
    runs-on: ubuntu-latest
    steps:
      - run: echo deploy
        if: ${{ secrets.VERCEL_TOKEN != '' }}
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(validate_workflows, "WORKFLOW_DIR", workflow_dir)

    assert validate_workflows.main() == 1


def test_validate_workflows_rejects_main_git_push(tmp_path: Path, monkeypatch) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "main.yml").write_text(
        """
name: Main
on:
  push:
    paths-ignore:
      - 'sources/batch_*.txt'
      - 'sources/backup_dynamic/**'
concurrency:
  group: main
jobs:
  data:
    runs-on: ubuntu-latest
    steps:
      - run: git push origin HEAD:main
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(validate_workflows, "WORKFLOW_DIR", workflow_dir)

    assert validate_workflows.main() == 1


def test_validate_workflows_rejects_short_pipeline_retention(
    tmp_path: Path, monkeypatch
) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "main.yml").write_text(
        """
name: Main
on:
  workflow_dispatch:
concurrency:
  group: main
jobs:
  data:
    runs-on: ubuntu-latest
    steps:
      - run: python scripts/dynamic_reshard.py
      - uses: actions/upload-artifact@v4
        with:
          name: source-reshard-recommendation
          path: sources/batch_*.txt
      - uses: actions/upload-artifact@v4
        with:
          name: pipeline-output
          path: output/
          retention-days: 3
      - run: |
          python scripts/validate_pages_artifact.py \
            --native-client-check \
            --native-report-file pipeline-evidence/native_client_check_report.json \
            output
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(validate_workflows, "WORKFLOW_DIR", workflow_dir)

    assert validate_workflows.main() == 1


def test_validate_workflows_rejects_retention_claim_outside_artifact_step(
    tmp_path: Path, monkeypatch
) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "main.yml").write_text(
        """
name: Main
on:
  workflow_dispatch:
concurrency:
  group: main
jobs:
  data:
    runs-on: ubuntu-latest
    steps:
      - run: |
          echo "pipeline-output retention-days: 30"
          python scripts/dynamic_reshard.py
      - uses: actions/upload-artifact@v4
        with:
          name: source-reshard-recommendation
          path: sources/batch_*.txt
      - uses: actions/upload-artifact@v4
        with:
          name: pipeline-output
          path: output/
      - run: |
          python scripts/validate_pages_artifact.py \
            --native-client-check \
            --native-report-file pipeline-evidence/native_client_check_report.json \
            output
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(validate_workflows, "WORKFLOW_DIR", workflow_dir)

    assert validate_workflows.main() == 1


def test_validate_workflows_accepts_numeric_string_pipeline_retention(
    tmp_path: Path, monkeypatch
) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "main.yml").write_text(
        """
name: Main
on:
  workflow_dispatch:
concurrency:
  group: main
jobs:
  data:
    runs-on: ubuntu-latest
    steps:
      - run: python scripts/dynamic_reshard.py
      - uses: actions/upload-artifact@v4
        with:
          name: source-reshard-recommendation
          path: sources/batch_*.txt
      - uses: actions/upload-artifact@v4
        with:
          name: pipeline-output
          path: output/
          retention-days: "30"
      - run: |
          python scripts/validate_pages_artifact.py \
            --native-client-check \
            --native-report-file pipeline-evidence/native_client_check_report.json \
            output
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(validate_workflows, "WORKFLOW_DIR", workflow_dir)

    assert validate_workflows.main() == 0


def test_validate_workflows_requires_native_client_report_for_main_release(
    tmp_path: Path, monkeypatch
) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "main.yml").write_text(
        """
name: Main
on:
  workflow_dispatch:
concurrency:
  group: main
jobs:
  data:
    runs-on: ubuntu-latest
    steps:
      - run: python scripts/dynamic_reshard.py
      - uses: actions/upload-artifact@v4
        with:
          name: source-reshard-recommendation
          path: sources/batch_*.txt
      - uses: actions/upload-artifact@v4
        with:
          name: pipeline-output
          path: output/
          retention-days: "30"
      - run: python scripts/validate_pages_artifact.py output
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(validate_workflows, "WORKFLOW_DIR", workflow_dir)

    assert validate_workflows.main() == 1


def test_validate_workflows_requires_shared_output_contract(
    tmp_path: Path, monkeypatch
) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "main.yml").write_text(
        """
name: Main
on:
  workflow_dispatch:
concurrency:
  group: main
jobs:
  data:
    runs-on: ubuntu-latest
    steps:
      - run: python scripts/dynamic_reshard.py
      - uses: actions/upload-artifact@v4
        with:
          name: source-reshard-recommendation
          path: sources/batch_*.txt
      - uses: actions/upload-artifact@v4
        with:
          name: pipeline-output
          path: output/
          retention-days: 30
      - run: |
          test -s output/singbox.json
          test -f output/base64.txt
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(validate_workflows, "WORKFLOW_DIR", workflow_dir)

    assert validate_workflows.main() == 1


def test_validate_workflows_rejects_short_pipeline_retention_retest(
    tmp_path: Path, monkeypatch
) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "retest.yml").write_text("""
name: Retest
on:
  workflow_dispatch:
concurrency:
  group: retest
jobs:
  data:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/upload-artifact@v4
        with:
          name: pipeline-output
          path: output/
          retention-days: 3
""")
    monkeypatch.setattr("scripts.validate_workflows.WORKFLOW_DIR", workflow_dir)
    assert validate_workflows.main() != 0


def test_validate_workflows_rejects_short_pipeline_retention_deploy_pages(
    tmp_path: Path, monkeypatch
) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "deploy-pages.yml").write_text("""
name: Deploy Pages
on:
  workflow_dispatch:
concurrency:
  group: pages
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/upload-pages-artifact@v3
        with:
          path: output
          retention-days: 7
""")
    monkeypatch.setattr("scripts.validate_workflows.WORKFLOW_DIR", workflow_dir)
    assert validate_workflows.main() != 0


def test_validate_workflows_rejects_pages_retention_claim_outside_upload_step(
    tmp_path: Path, monkeypatch
) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "deploy-pages.yml").write_text("""
name: Deploy Pages
on:
  workflow_dispatch:
concurrency:
  group: pages
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - run: |
          echo "upload-pages-artifact retention-days: 30"
          cp -R frontend/. output/
          python scripts/validate_frontend_placeholders.py --inject-env --strict output
          scripts/verify_pages_deployment.py
        env:
          CS_PUBLIC_KEY: ${{ secrets.CS_PUBLIC_KEY }}
          STEGO_KEY: ${{ secrets.STEGO_KEY }}
      - uses: actions/upload-pages-artifact@v3
        with:
          path: output
""")
    monkeypatch.setattr("scripts.validate_workflows.WORKFLOW_DIR", workflow_dir)
    assert validate_workflows.main() != 0
