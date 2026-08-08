# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

import pytest

from configstream.source_admission import (
    SourceAdmissionError,
    SourceAdmissionPolicy,
    classify_source_locator,
    normalize_source_locator,
    resolve_source_admission_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "src" / "configstream" / "data" / "source-admission.json"


def _batch_urls() -> set[str]:
    result: set[str] = set()
    for path in sorted((ROOT / "sources").glob("batch_*.txt")):
        result.update(
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    return result


def test_bundled_manifest_resolves_inside_package() -> None:
    assert resolve_source_admission_manifest("bundled") == MANIFEST
    assert MANIFEST.is_file()


def test_manifest_covers_every_tracked_batch_locator_exactly():
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    admitted = {entry["url"] for entry in payload["entries"]}
    assert admitted == _batch_urls()
    assert payload["entry_count"] == len(admitted)


def test_policy_accepts_admitted_and_rejects_unknown_source():
    policy = SourceAdmissionPolicy(MANIFEST)
    admitted = next(iter(policy.entries))
    assert policy.validate([admitted])[0].url == admitted
    assert len(policy.validate([admitted, admitted])) == 1
    with pytest.raises(SourceAdmissionError, match="not admitted"):
        policy.validate(["https://unreviewed.example/subscription.txt"])


def test_manifest_does_not_overstate_floating_github_identity():
    policy = SourceAdmissionPolicy(MANIFEST)
    floating = [
        entry
        for entry in policy.entries.values()
        if entry.locator_type == "github-raw" and not entry.immutable_reference
    ]
    assert floating
    assert all(entry.trust_class == "community-floating" for entry in floating)


def test_policy_blocks_plain_http_sources_from_default_fetch_set():
    policy = SourceAdmissionPolicy(MANIFEST)
    insecure = next(
        entry.url
        for entry in policy.entries.values()
        if entry.trust_class == "insecure-transport"
    )
    secure = next(
        entry.url
        for entry in policy.entries.values()
        if entry.trust_class != "insecure-transport"
    )
    accepted, blocked = policy.partition_fetchable([insecure, secure])
    assert [entry.url for entry in accepted] == [secure]
    assert [entry.url for entry in blocked] == [insecure]


def test_cli_keeps_admission_secure_by_default_with_explicit_local_override():
    source = (ROOT / "src" / "configstream" / "cli.py").read_text(encoding="utf-8")
    assert '"--allow-unadmitted-sources"' in source
    assert (
        "settings.ENFORCE_SOURCE_ADMISSION and not allow_unadmitted_sources" in source
    )
    assert "source admission was explicitly bypassed" in source
    assert "insecure-transport source(s)" in source


def test_policy_rejects_manifest_that_mislabels_plain_http_as_safe(tmp_path):
    url = "http://example.com/subscription.txt"
    payload = {
        "schema_version": 1,
        "source_set_sha256": __import__("hashlib")
        .sha256((url + "\n").encode())
        .hexdigest(),
        "entries": [
            {
                "url": url,
                "url_sha256": __import__("hashlib").sha256(url.encode()).hexdigest(),
                "host": "example.com",
                "scheme": "http",
                "locator_type": "opaque-http",
                "reference": None,
                "immutable_reference": False,
                "trust_class": "opaque",
            }
        ],
    }
    manifest = tmp_path / "source-admission.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SourceAdmissionError, match="insecure-transport"):
        SourceAdmissionPolicy(manifest)


def test_policy_rejects_manifest_url_metadata_mismatch(tmp_path):
    url = "https://example.com/subscription.txt"
    payload = {
        "schema_version": 1,
        "source_set_sha256": __import__("hashlib")
        .sha256((url + "\n").encode())
        .hexdigest(),
        "entries": [
            {
                "url": url,
                "url_sha256": __import__("hashlib").sha256(url.encode()).hexdigest(),
                "host": "other.example",
                "scheme": "https",
                "locator_type": "opaque-http",
                "reference": None,
                "immutable_reference": False,
                "trust_class": "opaque",
            }
        ],
    }
    manifest = tmp_path / "source-admission.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SourceAdmissionError, match="metadata mismatch"):
        SourceAdmissionPolicy(manifest)


def test_policy_rejects_overstated_immutable_reference(tmp_path):
    url = "https://raw.githubusercontent.com/example/project/main/list.txt"
    payload = {
        "schema_version": 1,
        "source_set_sha256": __import__("hashlib")
        .sha256((url + "\n").encode())
        .hexdigest(),
        "entries": [
            {
                "url": url,
                "url_sha256": __import__("hashlib").sha256(url.encode()).hexdigest(),
                "host": "raw.githubusercontent.com",
                "scheme": "https",
                "locator_type": "github-raw",
                "reference": "main",
                "immutable_reference": True,
                "trust_class": "community-immutable",
            }
        ],
    }
    manifest = tmp_path / "source-admission.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SourceAdmissionError, match="classification mismatch"):
        SourceAdmissionPolicy(manifest)


def test_policy_rejects_non_object_manifest_entry(tmp_path):
    payload = {
        "schema_version": 1,
        "source_set_sha256": __import__("hashlib").sha256(b"\n").hexdigest(),
        "entries": ["not-an-object"],
    }
    manifest = tmp_path / "source-admission.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SourceAdmissionError, match="must be an object"):
        SourceAdmissionPolicy(manifest)


def test_policy_entries_mapping_is_read_only():
    policy = SourceAdmissionPolicy(MANIFEST)
    with pytest.raises(TypeError):
        policy.entries["https://example.test"] = next(iter(policy.entries.values()))


@pytest.mark.parametrize(
    "url, message",
    [
        ("https://user:secret@example.com/list.txt", "credentials"),
        ("https://example.com:99999/list.txt", "invalid port"),
    ],
)
def test_policy_rejects_secret_bearing_or_invalid_locators(tmp_path, url, message):
    payload = {
        "schema_version": 1,
        "source_set_sha256": __import__("hashlib")
        .sha256((url + "\n").encode())
        .hexdigest(),
        "entries": [
            {
                "url": url,
                "url_sha256": __import__("hashlib").sha256(url.encode()).hexdigest(),
                "host": "example.com",
                "scheme": "https",
                "locator_type": "opaque-http",
                "reference": None,
                "immutable_reference": False,
                "trust_class": "opaque",
            }
        ],
    }
    manifest = tmp_path / "source-admission.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SourceAdmissionError, match=message):
        SourceAdmissionPolicy(manifest)


def test_locator_normalization_removes_client_only_fragment_and_default_port():
    assert (
        normalize_source_locator("HTTPS://Example.COM:443/list.txt?x=1#client-label")
        == "https://example.com/list.txt?x=1"
    )


def test_policy_rejects_noncanonical_manifest_url_but_normalizes_runtime_input(
    tmp_path,
):
    canonical = "https://example.com/list.txt"
    payload = {
        "schema_version": 1,
        "source_set_sha256": __import__("hashlib")
        .sha256((canonical + "\n").encode())
        .hexdigest(),
        "entries": [
            {
                "url": canonical,
                "url_sha256": __import__("hashlib")
                .sha256(canonical.encode())
                .hexdigest(),
                "host": "example.com",
                "scheme": "https",
                "locator_type": "opaque-http",
                "reference": None,
                "immutable_reference": False,
                "trust_class": "opaque",
            }
        ],
    }
    manifest = tmp_path / "source-admission.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    policy = SourceAdmissionPolicy(manifest)
    assert policy.validate([canonical + "#client-label"])[0].url == canonical

    fragment_url = canonical + "#client-label"
    payload["entries"][0]["url"] = fragment_url
    payload["entries"][0]["url_sha256"] = (
        __import__("hashlib").sha256(fragment_url.encode()).hexdigest()
    )
    payload["source_set_sha256"] = (
        __import__("hashlib").sha256((fragment_url + "\n").encode()).hexdigest()
    )
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SourceAdmissionError, match="not canonical"):
        SourceAdmissionPolicy(manifest)


def test_githubusercontent_classification_rejects_suffix_spoofing():
    legitimate = classify_source_locator(
        "https://objects.githubusercontent.com/example/list.txt"
    )
    spoofed = classify_source_locator(
        "https://evilgithubusercontent.com/example/list.txt"
    )

    assert legitimate["locator_type"] == "github-content"
    assert legitimate["trust_class"] == "community-floating"
    assert spoofed["locator_type"] == "opaque-http"
    assert spoofed["trust_class"] == "opaque"
