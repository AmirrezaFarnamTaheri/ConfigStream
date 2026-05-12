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
