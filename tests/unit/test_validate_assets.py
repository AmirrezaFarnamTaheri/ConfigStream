# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for tracked asset hygiene validation."""

from __future__ import annotations

from pathlib import Path

from scripts import validate_assets


def _patch_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(validate_assets, "ROOT", tmp_path)


def test_validate_zero_byte_accepts_intentional_markers(
    tmp_path: Path, monkeypatch
) -> None:
    _patch_root(tmp_path, monkeypatch)
    nojekyll = tmp_path / ".nojekyll"
    pytyped = tmp_path / "src" / "configstream" / "py.typed"
    pytyped.parent.mkdir(parents=True)
    nojekyll.write_bytes(b"")
    pytyped.write_bytes(b"")

    assert validate_assets._validate_zero_byte_files([nojekyll, pytyped]) == []


def test_validate_zero_byte_rejects_unallowlisted_file(
    tmp_path: Path, monkeypatch
) -> None:
    _patch_root(tmp_path, monkeypatch)
    empty = tmp_path / "frontend" / "assets" / "images" / "header-bg.png"
    empty.parent.mkdir(parents=True)
    empty.write_bytes(b"")

    errors = validate_assets._validate_zero_byte_files([empty])

    assert errors == [
        "tracked zero-byte file is not allowlisted: frontend/assets/images/header-bg.png"
    ]


def test_validate_image_references_accepts_existing_nonempty_asset(
    tmp_path: Path, monkeypatch
) -> None:
    _patch_root(tmp_path, monkeypatch)
    script = tmp_path / "frontend" / "assets" / "js" / "analytics.js"
    image = tmp_path / "frontend" / "assets" / "images" / "globe" / "earth.jpg"
    script.parent.mkdir(parents=True)
    image.parent.mkdir(parents=True)
    script.write_text('"assets/images/globe/earth.jpg";\n', encoding="utf-8")
    image.write_bytes(b"jpeg")

    assert validate_assets._validate_image_references([script, image]) == []


def test_validate_image_references_rejects_missing_asset(
    tmp_path: Path, monkeypatch
) -> None:
    _patch_root(tmp_path, monkeypatch)
    script = tmp_path / "frontend" / "assets" / "js" / "analytics.js"
    script.parent.mkdir(parents=True)
    script.write_text('"assets/images/globe/missing.jpg";\n', encoding="utf-8")

    errors = validate_assets._validate_image_references([script])

    assert errors == [
        "frontend/assets/js/analytics.js references missing image: "
        "assets/images/globe/missing.jpg"
    ]


def test_validate_image_references_skips_template_asset_refs(
    tmp_path: Path, monkeypatch
) -> None:
    _patch_root(tmp_path, monkeypatch)
    script = tmp_path / "frontend" / "assets" / "js" / "proxies.js"
    script.parent.mkdir(parents=True)
    script.write_text(
        '"assets/images/flags/w20/${normalizedCountryCode}.png";\n',
        encoding="utf-8",
    )

    assert validate_assets._validate_image_references([script]) == []


def test_validate_image_references_rejects_empty_asset(
    tmp_path: Path, monkeypatch
) -> None:
    _patch_root(tmp_path, monkeypatch)
    html = tmp_path / "frontend" / "index.html"
    image = tmp_path / "frontend" / "assets" / "images" / "empty.png"
    html.parent.mkdir(parents=True)
    image.parent.mkdir(parents=True)
    html.write_text('<img src="assets/images/empty.png">\n', encoding="utf-8")
    image.write_bytes(b"")

    errors = validate_assets._validate_image_references([html, image])

    assert errors == [
        "frontend/index.html references empty image: frontend/assets/images/empty.png"
    ]


def test_validator_uses_dependency_free_log_sanitizer() -> None:
    source = Path(validate_assets.__file__).read_text(encoding="utf-8")

    assert "configstream.security_validator" not in source
    assert "configstream.utils.log_sanitizer" in source

def test_resolve_svg_parser_returns_parse_capable_module() -> None:
    parser, parse_errors = validate_assets._resolve_svg_parser()

    assert hasattr(parser, "parse")
    assert parse_errors


def test_validate_svg_xml_rejects_malformed_svg(tmp_path: Path, monkeypatch) -> None:
    _patch_root(tmp_path, monkeypatch)
    svg = tmp_path / "frontend" / "assets" / "svg" / "broken.svg"
    svg.parent.mkdir(parents=True)
    svg.write_text("<svg><g></svg>", encoding="utf-8")

    errors = validate_assets._validate_svg_xml([svg])

    assert len(errors) == 1
    assert errors[0].startswith("malformed SVG XML in frontend/assets/svg/broken.svg:")


def test_validate_svg_xml_sanitizes_parser_diagnostics(
    tmp_path: Path, monkeypatch
) -> None:
    _patch_root(tmp_path, monkeypatch)
    svg = tmp_path / "frontend" / "assets" / "svg" / "broken.svg"
    svg.parent.mkdir(parents=True)
    svg.write_text("<svg/>", encoding="utf-8")

    class SensitiveParseError(Exception):
        pass

    class Parser:
        @staticmethod
        def parse(_path: Path) -> None:
            raise SensitiveParseError(
                "fetch https://user:password@example.test/?token=secret from 192.0.2.1"
            )

    monkeypatch.setattr(
        validate_assets,
        "_resolve_svg_parser",
        lambda: (Parser, (SensitiveParseError,)),
    )

    [error] = validate_assets._validate_svg_xml([svg])

    assert "password" not in error
    assert "token=secret" not in error
    assert "192.0.2.1" not in error
    assert "[MASKED]" in error
    assert "[IP]" in error
