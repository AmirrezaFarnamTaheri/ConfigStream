# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path
import shutil

from scripts.validate_container_pins import validate

def test_repository_container_images_are_digest_pinned_and_targets_are_separated() -> None:
    assert validate(Path('.')) == []


def test_container_validation_rejects_missing_bundled_source_admission_manifest(
    tmp_path: Path,
) -> None:
    for relative in (
        "Dockerfile",
        ".dockerignore",
        "config/container-images.json",
        ".github/workflows/main.yml",
        "render.yaml",
        "pyproject.toml",
        "src/configstream/data/source-admission.json",
    ):
        source = Path(relative)
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    (tmp_path / "src/configstream/data/source-admission.json").unlink()

    errors = validate(tmp_path)

    assert any("bundled source-admission.json" in error for error in errors)


def test_container_validation_rejects_missing_package_data_declaration(
    tmp_path: Path,
) -> None:
    for relative in (
        "Dockerfile",
        ".dockerignore",
        "config/container-images.json",
        ".github/workflows/main.yml",
        "render.yaml",
        "pyproject.toml",
        "src/configstream/data/source-admission.json",
    ):
        source = Path(relative)
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace(
            'configstream = ["data/*.json"]\n', ""
        ),
        encoding="utf-8",
    )

    errors = validate(tmp_path)

    assert any("JSON package data" in error for error in errors)
