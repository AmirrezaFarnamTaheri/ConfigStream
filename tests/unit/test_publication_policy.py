# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from datetime import datetime, timedelta, timezone

import pytest

from configstream.publication import (
    ArtifactPolicyError,
    validate_public_artifact,
    write_release_manifest,
)


def violation_codes(exc: ArtifactPolicyError) -> set[str]:
    return {item.code for item in exc.violations}


def test_valid_public_artifact_returns_stable_digests(tmp_path):
    (tmp_path / "metadata.json").write_text('{"total_working": 1}', encoding="utf-8")
    (tmp_path / "proxies.json").write_text("[]", encoding="utf-8")

    first = validate_public_artifact(
        tmp_path,
        allowed_paths={"metadata.json", "proxies.json"},
        required_paths={"metadata.json", "proxies.json"},
    )
    second = validate_public_artifact(
        tmp_path,
        allowed_paths={"metadata.json", "proxies.json"},
        required_paths={"metadata.json", "proxies.json"},
    )
    assert first == second


def test_private_cache_is_rejected_even_when_allowlisted(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "test_cache.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ArtifactPolicyError) as raised:
        validate_public_artifact(
            tmp_path,
            allowed_paths={"data/test_cache.json"},
        )
    assert "private_file" in violation_codes(raised.value)


def test_tokenized_source_url_is_rejected(tmp_path):
    (tmp_path / "proxies.json").write_text(
        json.dumps({"source": "https://provider.example/sub?token=canary-secret"}),
        encoding="utf-8",
    )

    with pytest.raises(ArtifactPolicyError) as raised:
        validate_public_artifact(tmp_path, allowed_paths={"proxies.json"})
    assert "secret_material" in violation_codes(raised.value)


def test_unknown_file_is_rejected(tmp_path):
    (tmp_path / "unexpected.txt").write_text("hello", encoding="utf-8")
    with pytest.raises(ArtifactPolicyError) as raised:
        validate_public_artifact(tmp_path, allowed_paths=set())
    assert "unexpected_file" in violation_codes(raised.value)


def test_missing_required_file_is_rejected(tmp_path):
    with pytest.raises(ArtifactPolicyError) as raised:
        validate_public_artifact(
            tmp_path,
            allowed_paths={"metadata.json"},
            required_paths={"metadata.json"},
        )
    assert "missing_required_file" in violation_codes(raised.value)


def test_release_manifest_is_content_addressed(tmp_path):
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    first = write_release_manifest(
        tmp_path / "release.json",
        source_commit_sha="a" * 40,
        workflow_sha="b" * 40,
        image_digest="sha256:" + "c" * 64,
        policy_digest="d" * 64,
        artifact_digests={"proxies.json": "e" * 64},
        expires_at=expires,
    )
    written = json.loads((tmp_path / "release.json").read_text(encoding="utf-8"))
    assert written == first
    assert len(first["release_id"]) == 64


def test_symlink_is_rejected(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("secret", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this platform")
    with pytest.raises(ArtifactPolicyError) as raised:
        validate_public_artifact(tmp_path, allowed_paths={"link.txt"})
    assert "symlink_forbidden" in violation_codes(raised.value)
