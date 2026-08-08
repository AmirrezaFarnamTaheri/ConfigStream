# SPDX-License-Identifier: AGPL-3.0-or-later
"""Repository-maintained source admission policy.

This module does not claim that an upstream source is trustworthy. It proves only
that a locator was reviewed into the checked-in source set and records whether
its upstream identity is immutable, floating, or opaque.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Iterable, Mapping
from urllib.parse import urlsplit, urlunsplit

from .errors import SourcePolicyError

_COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")


class SourceAdmissionError(SourcePolicyError, ValueError):
    """Raised when one or more source locators are outside the admitted set."""


def normalize_source_locator(url: str) -> str:
    """Return the exact HTTP fetch identity for one source locator.

    URL fragments are client-side labels and are never sent to the upstream
    server, so they are removed from the canonical fetch identity. Credentials
    remain forbidden because source locators are committed and logged.
    """
    value = str(url).strip()
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as exc:
        raise SourceAdmissionError(
            "source admission entry has an invalid port"
        ) from exc

    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"} or not parsed.hostname:
        raise SourceAdmissionError("source admission entry has invalid URL")
    if parsed.username is not None or parsed.password is not None:
        raise SourceAdmissionError("source admission URL must not contain credentials")
    if port is not None and not 1 <= port <= 65535:
        raise SourceAdmissionError("source admission entry has an invalid port")

    host = parsed.hostname.lower()
    rendered_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    default_port = (scheme == "https" and port == 443) or (
        scheme == "http" and port == 80
    )
    netloc = (
        rendered_host if port is None or default_port else f"{rendered_host}:{port}"
    )
    return urlunsplit((scheme, netloc, parsed.path, parsed.query, ""))


def classify_source_locator(url: str) -> dict[str, object]:
    """Validate and derive immutable metadata for one exact fetch locator."""
    canonical_url = normalize_source_locator(url)
    parsed = urlsplit(canonical_url)
    host = parsed.hostname or ""
    scheme = parsed.scheme
    path_parts = [part for part in parsed.path.split("/") if part]
    locator_type = "opaque-http"
    reference: str | None = None
    if host == "raw.githubusercontent.com" and len(path_parts) >= 3:
        locator_type = "github-raw"
        reference = path_parts[2]
        if reference == "refs" and len(path_parts) >= 5:
            reference = "/".join(path_parts[2:5])
    elif host == "github.com" and len(path_parts) >= 5 and path_parts[2] == "raw":
        locator_type = "github-raw"
        reference = path_parts[3]
    elif host == "githubusercontent.com" or host.endswith(".githubusercontent.com"):
        locator_type = "github-content"

    immutable = bool(reference and _COMMIT_RE.fullmatch(reference))
    if scheme != "https":
        trust_class = "insecure-transport"
    elif immutable:
        trust_class = "community-immutable"
    elif locator_type.startswith("github"):
        trust_class = "community-floating"
    else:
        trust_class = "opaque"
    return {
        "url": canonical_url,
        "url_sha256": hashlib.sha256(canonical_url.encode("utf-8")).hexdigest(),
        "host": host,
        "scheme": scheme,
        "locator_type": locator_type,
        "reference": reference,
        "immutable_reference": immutable,
        "trust_class": trust_class,
    }


@dataclass(frozen=True)
class SourceAdmissionEntry:
    url: str
    url_sha256: str
    host: str
    scheme: str
    locator_type: str
    reference: str | None
    immutable_reference: bool
    trust_class: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "SourceAdmissionEntry":
        url = str(value.get("url", ""))
        expected_digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        digest = str(value.get("url_sha256", ""))
        if not url or digest != expected_digest:
            raise SourceAdmissionError("source admission entry digest mismatch")
        expected = classify_source_locator(url)
        if url != expected["url"]:
            raise SourceAdmissionError("source admission URL is not canonical")
        for field in (
            "host",
            "scheme",
            "locator_type",
            "reference",
            "immutable_reference",
            "trust_class",
        ):
            if value.get(field) != expected[field]:
                if field == "trust_class" and expected[field] == "insecure-transport":
                    raise SourceAdmissionError(
                        "non-HTTPS source must be classified as insecure-transport"
                    )
                raise SourceAdmissionError(
                    "source admission metadata mismatch (classification mismatch)"
                )
        return cls(
            url=url,
            url_sha256=digest,
            host=str(expected["host"]),
            scheme=str(expected["scheme"]),
            locator_type=str(expected["locator_type"]),
            reference=(
                str(expected["reference"])
                if expected["reference"] is not None
                else None
            ),
            immutable_reference=bool(expected["immutable_reference"]),
            trust_class=str(expected["trust_class"]),
        )


class SourceAdmissionPolicy:
    """Load and enforce exact source locators from a deterministic manifest."""

    def __init__(self, manifest_path: str | Path) -> None:
        self.manifest_path = Path(manifest_path)
        payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != 1:
            raise SourceAdmissionError("unsupported source admission schema")
        raw_entries = payload.get("entries")
        if not isinstance(raw_entries, list):
            raise SourceAdmissionError("source admission entries must be a list")
        entries_list: list[SourceAdmissionEntry] = []
        for item in raw_entries:
            if not isinstance(item, Mapping):
                raise SourceAdmissionError("source admission entry must be an object")
            entries_list.append(SourceAdmissionEntry.from_mapping(item))
        entries = tuple(entries_list)
        urls = [entry.url for entry in entries]
        if len(urls) != len(set(urls)):
            raise SourceAdmissionError(
                "source admission manifest contains duplicate URLs"
            )
        computed_set_digest = hashlib.sha256(
            ("\n".join(sorted(urls)) + "\n").encode("utf-8")
        ).hexdigest()
        if payload.get("source_set_sha256") != computed_set_digest:
            raise SourceAdmissionError("source admission set digest mismatch")
        self._entries = MappingProxyType({entry.url: entry for entry in entries})

    @property
    def entries(self) -> Mapping[str, SourceAdmissionEntry]:
        return self._entries

    def validate(self, sources: Iterable[str]) -> tuple[SourceAdmissionEntry, ...]:
        normalized_values: list[str] = []
        for source in sources:
            value = str(source).strip()
            if value:
                normalized_values.append(normalize_source_locator(value))
        normalized = tuple(dict.fromkeys(normalized_values))
        missing = sorted(
            {source for source in normalized if source not in self._entries}
        )
        if missing:
            preview = ", ".join(missing[:3])
            suffix = "" if len(missing) <= 3 else f" (+{len(missing) - 3} more)"
            raise SourceAdmissionError(
                f"{len(missing)} source locator(s) are not admitted: {preview}{suffix}"
            )
        return tuple(self._entries[source] for source in normalized)

    def partition_fetchable(
        self,
        sources: Iterable[str],
        *,
        blocked_trust_classes: frozenset[str] = frozenset({"insecure-transport"}),
    ) -> tuple[tuple[SourceAdmissionEntry, ...], tuple[SourceAdmissionEntry, ...]]:
        entries = self.validate(sources)
        blocked = tuple(
            entry for entry in entries if entry.trust_class in blocked_trust_classes
        )
        accepted = tuple(
            entry for entry in entries if entry.trust_class not in blocked_trust_classes
        )
        return accepted, blocked


def resolve_source_admission_manifest(value: str | Path) -> Path:
    """Resolve the stable bundled manifest or an explicit operator override."""

    if str(value).strip() == "bundled":
        return Path(__file__).resolve().parent / "data" / "source-admission.json"
    return Path(value).expanduser()


def validate_admitted_sources(
    sources: Iterable[str],
    *,
    manifest_path: str | Path,
) -> tuple[SourceAdmissionEntry, ...]:
    return SourceAdmissionPolicy(manifest_path).validate(sources)


def partition_fetchable_sources(
    sources: Iterable[str],
    *,
    manifest_path: str | Path,
) -> tuple[tuple[SourceAdmissionEntry, ...], tuple[SourceAdmissionEntry, ...]]:
    return SourceAdmissionPolicy(manifest_path).partition_fetchable(sources)
