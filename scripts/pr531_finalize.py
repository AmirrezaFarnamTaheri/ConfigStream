#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Apply the final review remediation set for PR 531.

This script is intentionally temporary. The companion one-shot workflow removes
it after the repository's own formatters and focused tests pass.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETUP_PYTHON_SHA = "5fda3b95a4ea91299a34e894583c3862153e4b97"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, value: str) -> None:
    (ROOT / path).write_text(value, encoding="utf-8")


def replace(path: str, old: str, new: str, *, required: bool = True) -> bool:
    value = read(path)
    if old not in value:
        if required:
            raise RuntimeError(f"required pattern missing in {path}: {old[:120]!r}")
        return False
    write(path, value.replace(old, new))
    return True


def regex_replace(
    path: str,
    pattern: str,
    replacement: str,
    *,
    count: int = 0,
    required: bool = True,
    flags: int = 0,
) -> int:
    value = read(path)
    updated, matches = re.subn(pattern, replacement, value, count=count, flags=flags)
    if required and matches == 0:
        raise RuntimeError(f"required regex missing in {path}: {pattern!r}")
    if matches:
        write(path, updated)
    return matches


def pin_setup_python() -> None:
    replacement = f"actions/setup-python@{SETUP_PYTHON_SHA} # v7"
    for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        value = path.read_text(encoding="utf-8")
        updated = value.replace("actions/setup-python@v7", replacement)
        if updated != value:
            path.write_text(updated, encoding="utf-8")


def patch_workflows() -> None:
    pin_setup_python()
    replace(
        ".github/workflows/main.yml",
        f'''      - uses: actions/setup-python@{SETUP_PYTHON_SHA} # v7
        with:
          python-version: "3.11"
          cache: pip
      - uses: actions/setup-go@v7
        with:
          go-version: '1.24'
          cache-dependency-path: src/go/tester/go.sum
''',
        f'''      - uses: actions/setup-python@{SETUP_PYTHON_SHA} # v7
        with:
          python-version: "3.11"
      - uses: actions/setup-go@v7
        with:
          go-version: '1.24'
          cache: false
''',
    )
    replace(
        ".github/workflows/deploy_mirror.yml",
        '''          python - <<'PY'
          import json
          import os
          from datetime import datetime, timezone
          from pathlib import Path

          manifest = json.loads(Path("output/release_manifest.json").read_text(encoding="utf-8"))
          expires = datetime.fromisoformat(str(manifest["expires_at"]).replace("Z", "+00:00"))
''',
        '''          python3 - <<'PY'
          import json
          import os
          from datetime import datetime, timezone
          from pathlib import Path

          try:
              manifest = json.loads(
                  Path("output/release_manifest.json").read_text(encoding="utf-8")
              )
          except (OSError, UnicodeError, json.JSONDecodeError) as exc:
              raise SystemExit(f"release manifest is unreadable: {type(exc).__name__}") from exc
          if not isinstance(manifest, dict):
              raise SystemExit("release manifest must be a JSON object")
          raw_expiry = manifest.get("expires_at")
          if not isinstance(raw_expiry, str) or not raw_expiry.strip():
              raise SystemExit("release manifest is missing a valid expires_at")
          try:
              expires = datetime.fromisoformat(raw_expiry.replace("Z", "+00:00"))
          except ValueError as exc:
              raise SystemExit("release manifest has an invalid expires_at") from exc
          if expires.tzinfo is None or expires.utcoffset() is None:
              raise SystemExit("release manifest expires_at must be timezone-aware")
''',
    )


def patch_publication() -> None:
    publication = textwrap.dedent('''\
        # SPDX-License-Identifier: AGPL-3.0-or-later
        """Fail-closed public artifact validation and release identity."""

        from __future__ import annotations

        import hashlib
        import json
        import os
        import re
        from dataclasses import dataclass
        from datetime import datetime, timezone
        from pathlib import Path, PurePosixPath
        from typing import Iterable, Mapping

        PUBLIC_PRIVATE_BASENAMES = frozenset(
            {
                "test_cache.json",
                "source_quality.db",
                "anomaly.db",
                "history.db",
                "pipeline_events.jsonl",
                "consolidated_pipeline.log",
            }
        )
        PUBLIC_PRIVATE_SUFFIXES = frozenset(
            {".db", ".sqlite", ".sqlite3", ".log", ".lock", ".tmp"}
        )
        _PRIVATE_BASENAMES = PUBLIC_PRIVATE_BASENAMES
        _PRIVATE_SUFFIXES = PUBLIC_PRIVATE_SUFFIXES
        _HEX40 = re.compile(r"^[0-9a-f]{40}$")
        _HEX64 = re.compile(r"^[0-9a-f]{64}$")
        _IMAGE_DIGEST = re.compile(r"^(?:[^@\\s]+@)?sha256:[0-9a-f]{64}$")
        _SECRET_PATTERNS = (
            re.compile(
                r"(?i)https?://[^\\s\\\"']+[?&](?:token|api[_-]?key|key|auth|signature|sig)="
                r"(?!example|placeholder|your[-_])[A-Za-z0-9._~+/=-]{8,}"
            ),
            re.compile(r"(?i)authorization\\s*[:=]\\s*[\\\"']?bearer\\s+[A-Za-z0-9._~+/=-]{12,}"),
            re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
            re.compile(r"\\bgh[pousr]_[A-Za-z0-9]{30,}\\b"),
            re.compile(r"\\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\\b"),
        )


        @dataclass(frozen=True)
        class ArtifactViolation:
            code: str
            path: str
            message: str


        class ArtifactPolicyError(ValueError):
            def __init__(self, violations: Iterable[ArtifactViolation]) -> None:
                self.violations = tuple(violations)
                rendered = "; ".join(
                    f"{item.code}({item.path}): {item.message}"
                    for item in self.violations
                )
                super().__init__(rendered or "public artifact rejected")


        def _relative_entries(root: Path) -> list[Path]:
            return sorted(
                path
                for path in root.rglob("*")
                if path.is_file() or path.is_symlink()
            )


        def _is_private_path(relative: PurePosixPath) -> bool:
            if relative.name in _PRIVATE_BASENAMES:
                return True
            if relative.suffix.lower() in _PRIVATE_SUFFIXES:
                return True
            lowered_parts = {part.lower() for part in relative.parts}
            return bool(lowered_parts & {"private", "private-state", "fingerprints"})


        def validate_public_artifact(
            public_root: Path,
            *,
            allowed_paths: Iterable[str],
            required_paths: Iterable[str] = (),
            max_file_bytes: int = 64 * 1024 * 1024,
        ) -> Mapping[str, str]:
            """Validate exact public membership, symlinks, size, secrets, and hashes."""

            root = Path(public_root)
            if not root.is_dir():
                raise ArtifactPolicyError(
                    [ArtifactViolation("missing_public_root", str(root), "directory does not exist")]
                )
            if max_file_bytes <= 0:
                raise ValueError("max_file_bytes must be positive")

            allowed = {PurePosixPath(path).as_posix() for path in allowed_paths}
            required = {PurePosixPath(path).as_posix() for path in required_paths}
            actual: set[str] = set()
            digests: dict[str, str] = {}
            violations: list[ArtifactViolation] = []

            for path in _relative_entries(root):
                relative = PurePosixPath(path.relative_to(root).as_posix())
                rel = relative.as_posix()
                actual.add(rel)
                if path.is_symlink():
                    violations.append(
                        ArtifactViolation(
                            "symlink_forbidden",
                            rel,
                            "symbolic links are forbidden in public artifacts",
                        )
                    )
                    continue
                if _is_private_path(relative):
                    violations.append(
                        ArtifactViolation("private_file", rel, "private runtime state is forbidden")
                    )
                if rel not in allowed:
                    violations.append(
                        ArtifactViolation("unexpected_file", rel, "path is not in public allowlist")
                    )
                try:
                    size = path.stat().st_size
                except OSError as exc:
                    violations.append(
                        ArtifactViolation("unreadable_file", rel, type(exc).__name__)
                    )
                    continue
                if size > max_file_bytes:
                    violations.append(
                        ArtifactViolation("file_too_large", rel, f"{size} exceeds {max_file_bytes}")
                    )
                    continue
                try:
                    content = path.read_bytes()
                except OSError as exc:
                    violations.append(
                        ArtifactViolation("unreadable_file", rel, type(exc).__name__)
                    )
                    continue
                digests[rel] = hashlib.sha256(content).hexdigest()
                if b"\\x00" not in content:
                    text = content.decode("utf-8", errors="replace")
                    for pattern in _SECRET_PATTERNS:
                        if pattern.search(text):
                            violations.append(
                                ArtifactViolation(
                                    "secret_material",
                                    rel,
                                    f"matched public secret rule {pattern.pattern!r}",
                                )
                            )
                            break

            for missing in sorted(required - actual):
                violations.append(
                    ArtifactViolation("missing_required_file", missing, "required public file absent")
                )
            if violations:
                raise ArtifactPolicyError(violations)
            return dict(sorted(digests.items()))


        def _validate_identity(
            source_commit_sha: str,
            workflow_sha: str,
            image_digest: str,
            policy_digest: str,
            artifact_digests: Mapping[str, str],
        ) -> None:
            if not _HEX40.fullmatch(source_commit_sha):
                raise ValueError("source_commit_sha must be a lowercase 40-character Git SHA")
            if not _HEX40.fullmatch(workflow_sha):
                raise ValueError("workflow_sha must be a lowercase 40-character Git SHA")
            if not _IMAGE_DIGEST.fullmatch(image_digest):
                raise ValueError("image_digest must be an immutable sha256 digest")
            if not _HEX64.fullmatch(policy_digest):
                raise ValueError("policy_digest must be a lowercase SHA-256 hex digest")
            for path, value in artifact_digests.items():
                if not path or not _HEX64.fullmatch(value):
                    raise ValueError(f"invalid artifact digest for {path!r}")


        def write_release_manifest(
            destination: Path,
            *,
            source_commit_sha: str,
            workflow_sha: str,
            image_digest: str,
            policy_digest: str,
            artifact_digests: Mapping[str, str],
            expires_at: datetime,
            parent_release_digest: str | None = None,
        ) -> dict[str, object]:
            """Write a validated canonical, content-addressed release manifest."""

            _validate_identity(
                source_commit_sha,
                workflow_sha,
                image_digest,
                policy_digest,
                artifact_digests,
            )
            now = datetime.now(timezone.utc)
            if expires_at.tzinfo is None or expires_at.utcoffset() is None:
                raise ValueError("expires_at must be timezone-aware")
            if expires_at <= now:
                raise ValueError("expires_at must be in the future")
            if parent_release_digest is not None and not _HEX64.fullmatch(parent_release_digest):
                raise ValueError("parent_release_digest must be a SHA-256 hex digest")

            payload: dict[str, object] = {
                "schema_version": "1",
                "source_commit_sha": source_commit_sha,
                "workflow_sha": workflow_sha,
                "image_digest": image_digest,
                "policy_digest": policy_digest,
                "artifact_digests": dict(sorted(artifact_digests.items())),
                "generated_at": now.isoformat(),
                "expires_at": expires_at.astimezone(timezone.utc).isoformat(),
                "parent_release_digest": parent_release_digest,
            }
            canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            payload["release_id"] = hashlib.sha256(canonical).hexdigest()
            destination = Path(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
            temporary.write_text(
                json.dumps(payload, sort_keys=True, indent=2) + "\\n", encoding="utf-8"
            )
            temporary.replace(destination)
            return payload
        ''')
    write("src/configstream/publication.py", publication)


def patch_finalize_release() -> None:
    replace(
        "scripts/finalize_release.py",
        "from configstream.publication import validate_public_artifact, write_release_manifest\n\nPRIVATE_NAMES = {\n    \"test_cache.json\",\n    \"source_quality.db\",\n    \"anomaly.db\",\n    \"history.db\",\n    \"pipeline_events.jsonl\",\n    \"consolidated_pipeline.log\",\n}\nPRIVATE_SUFFIXES = {\".db\", \".sqlite\", \".sqlite3\", \".log\", \".lock\", \".tmp\"}\n",
        "from configstream.publication import (\n    PUBLIC_PRIVATE_BASENAMES as PRIVATE_NAMES,\n    PUBLIC_PRIVATE_SUFFIXES as PRIVATE_SUFFIXES,\n    validate_public_artifact,\n    write_release_manifest,\n)\n",
    )
    replace(
        "scripts/finalize_release.py",
        "def _partition_and_normalize_public_records(\n",
        "def _sort_port(item: dict[str, Any]) -> int:\n    try:\n        return int(item.get(\"port\") or 0)\n    except (TypeError, ValueError) as exc:\n        raise SystemExit(\"release rejected: proxy record has a non-numeric port\") from exc\n\n\ndef _partition_and_normalize_public_records(\n",
    )
    replace(
        "scripts/finalize_release.py",
        '            int(item.get("port") or 0),',
        "            _sort_port(item),",
    )
    replace(
        "scripts/finalize_release.py",
        '    tested = int(metadata.get("total_tested", metadata.get("tested", 0)) or 0)',
        '    tested = int(metadata.get("total_tested") or metadata.get("tested") or 0)',
    )
    replace(
        "scripts/finalize_release.py",
        '''    allowed = {
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
    }
''',
        '''    contract_path = Path(__file__).resolve().parents[1] / "docs" / "output_matrix.json"
    contract = _load_json(contract_path)
    declared = {
        str(item["path"])
        for item in contract.get("outputs", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    } if isinstance(contract, dict) else set()
    exact_known = {
        "proxies.json",
        "metadata.json",
        "health.json",
        "format_compatibility.json",
        "artifact_manifest.json",
        "pipeline_events.jsonl",
        ".nojekyll",
    }
    approved_prefixes = ("api/", "assets/", "data/", "docs/", "evidence/", "experimental/", "tools/")
    approved_suffixes = {
        ".css", ".html", ".ico", ".js", ".json", ".jsonl", ".map",
        ".md", ".png", ".svg", ".txt", ".wasm", ".webmanifest", ".yaml", ".yml", ".zip",
    }
    allowed = declared | exact_known
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith(approved_prefixes) and path.suffix.lower() in approved_suffixes:
            allowed.add(rel)
''',
    )


def patch_client_formats() -> None:
    replace(
        "src/configstream/output/client_formats.py",
        '''    except (TypeError, ValueError):
        return None
    result: dict[str, Any] = {"tag": tag}
''',
        '''    except (TypeError, ValueError):
        return None
    if kind != "wireguard" and (
        not isinstance(address, str) or not address.strip() or not 1 <= port <= 65535
    ):
        return None
    result: dict[str, Any] = {"tag": tag}
''',
    )
    replace(
        "src/configstream/output/client_formats.py",
        '''    elif kind in {"shadowsocks", "ss"}:
        result.update(
''',
        '''    elif kind in {"shadowsocks", "ss"}:
        if not outbound.get("method") or not outbound.get("password"):
            return None
        result.update(
''',
    )
    replace(
        "src/configstream/output/client_formats.py",
        '''        for candidate in candidates:
            base = _clean_tag(candidate.get("tag"), f"{protocol}-{len(seen) + 1}")
            tag = _unique_tag(base, seen)
            converted = _xray_outbound(candidate, tag)
            if converted:
                outbounds.append(converted)
''',
        '''        tag_map: dict[str, str] = {}
        pending: list[tuple[dict[str, Any], str]] = []
        for candidate in candidates:
            original = str(candidate.get("tag") or "")
            base = _clean_tag(candidate.get("tag"), f"{protocol}-{len(seen) + 1}")
            if base in _XRAY_BUILTIN_TAGS:
                base = f"proxy-{base}"
            tag = base
            suffix = 2
            while tag in seen or any(item[1] == tag for item in pending):
                tag = f"{base}-{suffix}"
                suffix += 1
            pending.append((candidate, tag))
            if original:
                tag_map[original] = tag
        for candidate, tag in pending:
            detour = candidate.get("detour")
            if detour and str(detour) in tag_map:
                candidate = {**candidate, "detour": tag_map[str(detour)]}
            converted = _xray_outbound(candidate, tag)
            if converted:
                seen.add(tag)
                outbounds.append(converted)
''',
    )


def patch_small_current_findings() -> None:
    replace(
        "src/configstream/dns_utils.py",
        '    return raw_host.strip("[]")',
        '    normalized = raw_host.strip("[]")\n    return normalized or None',
        required=False,
    )
    regex_replace(
        "scripts/repo_topology.py",
        r'''    while "//" in text:\n        text = text\.replace\("//", "/"\)\n    if not text\.startswith\("repo://"\):\n        text = "repo://" \+ text''',
        '''    if text.startswith("repo://"):
        suffix = text[len("repo://") :]
        while "//" in suffix:
            suffix = suffix.replace("//", "/")
        text = "repo://" + suffix.lstrip("/")
    else:
        while "//" in text:
            text = text.replace("//", "/")
        text = "repo://" + text''',
        required=False,
    )
    replace(
        "src/configstream/parsers/generic.py",
        '''            if method is not None and not isinstance(method, str):
                # The value comes from untrusted JSON; a non-string cipher would
                # otherwise raise AttributeError at method.lower() below.
                method = str(method)
''',
        '''            if method is not None and not isinstance(method, str):
                # Untrusted JSON: non-string ciphers are invalid; fail closed.
                return None
''',
        required=False,
    )
    replace(
        "src/configstream/circuit_breaker.py",
        "    def __init__(self, failure_threshold: int, recovery_timeout: float):",
        "    def __init__(self, failure_threshold: int, recovery_timeout: float) -> None:",
        required=False,
    )
    replace(
        "docs/client_format_contracts.md",
        "the repaired focused suite",
        "the repair-focused suite",
        required=False,
    )
    replace(
        "src/configstream/generators/clash.py",
        "Mihomo relay group",
        "Mihomo dialer-proxy relationship without a deprecated relay group",
        required=False,
    )
    replace(
        "tests/unit/test_client_format_contracts.py",
        'Path("docs/output_matrix.json")',
        'Path(__file__).resolve().parents[2] / "docs" / "output_matrix.json"',
        required=False,
    )
    replace(
        "tests/unit/test_output.py",
        '            password="dummy",\n',
        '            password="dummy",  # noqa: S106\n',
        required=False,
    )
    replace(
        "src/configstream/sources/__init__.py",
        '    "SourceProvider",\n    "SourcePolicyError",',
        '    "SourcePolicyError",\n    "SourceProvider",',
        required=False,
    )

    value = read("scripts/validate_frontend_placeholders.py")
    value = value.replace(
        r're.search(r"\\b(?:STEGO_KEY|CONFIG_STREAM_KEY)\\s*:", runtime_config)',
        r're.search(r"""(?:\\b(?:STEGO_KEY|CONFIG_STREAM_KEY)\\b|[\"\'](?:STEGO_KEY|CONFIG_STREAM_KEY)[\"\'])\\s*:""", runtime_config)',
    )
    value = value.replace(
        "if re.search(r'PUBLIC_KEY:\\\\s*\"\"', runtime_config):",
        '''if not re.search(
                r"""(?:\\bPUBLIC_KEY\\b|["']PUBLIC_KEY["'])\\s*:\\s*(?P<q>["'])(?P<value>[^"']+)\\1""",
                runtime_config,
            ):''',
    )
    write("scripts/validate_frontend_placeholders.py", value)

    policy_path = "src/configstream/sources/policy.py"
    policy = read(policy_path)
    marker = '''    if provider.license_spdx and snapshot.license_spdx != provider.license_spdx:
'''
    if "protocol_not_declared" not in policy and marker in policy:
        insert_at = policy.find("\n    if ", policy.find(marker) + len(marker))
        if insert_at != -1:
            addition = '''
    if (
        snapshot.protocol_claim is not None
        and provider.declared_protocols
        and snapshot.protocol_claim not in provider.declared_protocols
    ):
        violations.append(
            SourcePolicyViolation(
                "protocol_not_declared",
                f"protocol claim {snapshot.protocol_claim!r} is not declared by provider",
            )
        )
'''
            policy = policy[:insert_at] + addition + policy[insert_at:]
            write(policy_path, policy)


def patch_storage() -> None:
    path = "src/configstream/quality/storage.py"
    value = read(path).replace("import uuid\n", "")
    value = value.replace("SCHEMA_VERSION = 2", "SCHEMA_VERSION = 3")
    value = value.replace(
        "        self._all_connections: set[sqlite3.Connection] = set()\n        self._init_db()",
        "        self._all_connections: set[sqlite3.Connection] = set()\n        self._generation = 0\n        self._init_db()",
    )
    value = value.replace(
        '''        conn = getattr(self._thread_local, "conn", None)
        if conn is None:
''',
        '''        conn = getattr(self._thread_local, "conn", None)
        if conn is not None and getattr(self._thread_local, "generation", -1) != self._generation:
            self._thread_local.conn = None
            conn = None
        if conn is None:
''',
    )
    value = value.replace(
        '''            self._thread_local.conn = conn
            with self._lock:
''',
        '''            self._thread_local.conn = conn
            self._thread_local.generation = self._generation
            with self._lock:
''',
    )
    old_transaction = '''    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
'''
    new_transaction = '''    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            conn = self._get_conn()
            depth = int(getattr(self._thread_local, "transaction_depth", 0))
            self._thread_local.transaction_depth = depth + 1
            try:
                if depth == 0:
                    conn.execute("BEGIN IMMEDIATE")
                yield conn
                if depth == 0:
                    conn.commit()
            except Exception:
                if depth == 0:
                    conn.rollback()
                raise
            finally:
                self._thread_local.transaction_depth = depth
'''
    if old_transaction not in value:
        raise RuntimeError("storage transaction pattern changed")
    value = value.replace(old_transaction, new_transaction)
    value = value.replace(
        '''            self._thread_local.conn = None
        with self._lock:
            for tracked in self._all_connections:
''',
        '''            self._thread_local.conn = None
        with self._lock:
            self._generation += 1
            for tracked in self._all_connections:
''',
    )
    value = re.sub(
        r'''    @staticmethod\n    def _run_key\(url: str, run_data: Dict\[str, Any\]\) -> str:\n.*?        return hashlib\.sha256\(canonical\.encode\("utf-8"\)\)\.hexdigest\(\)\n''',
        '''    @staticmethod
    def _run_key(url: str, run_data: Dict[str, Any]) -> str:
        supplied = run_data.get("run_key") or run_data.get("event_id")
        if supplied:
            return str(supplied)
        canonical = json.dumps(
            {
                "url": url,
                "run_id": run_data.get("run_id"),
                "shard_id": run_data.get("shard_id"),
                "timestamp": run_data.get("timestamp"),
                "duration_ms": run_data.get("duration_ms", 0.0),
                "fetched_count": run_data.get("fetched_count", 0),
                "working_count": run_data.get("working_count", 0),
                "geoip_json": run_data.get("geoip_json", "{}"),
                "failure_modes_json": run_data.get("failure_modes_json", "{}"),
                "batch_source": run_data.get("batch_source"),
                "consumer_id": run_data.get("consumer_id"),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
''',
        value,
        count=1,
        flags=re.DOTALL,
    )
    value = value.replace(
        '''            with self._transaction() as conn:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO source_runs(
''',
        '''            with self._transaction() as conn:
                conn.execute(
                    "INSERT INTO source_stats(url) VALUES (?) "
                    "ON CONFLICT(url) DO NOTHING",
                    (url,),
                )
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO source_runs(
''',
        1,
    )
    value = value.replace(
        '''                for row in run_rows:
                    data = dict(row)
                    run_key = data.get("run_key") or self._run_key(
''',
        '''                for row in run_rows:
                    data = dict(row)
                    run_url = str(data.get("url") or "")
                    if not run_url:
                        continue
                    dst.execute(
                        "INSERT INTO source_stats(url) VALUES (?) "
                        "ON CONFLICT(url) DO NOTHING",
                        (run_url,),
                    )
                    run_key = data.get("run_key") or self._run_key(
''',
    )
    value = value.replace('str(data.get("url", "")), data', 'run_url, data')
    value = value.replace("                            data.get(\"url\"),", "                            run_url,")
    value = value.replace(
        '''        other = Path(other_db_path)
        if not other.exists():
            return
        try:
            src = sqlite3.connect(other)
''',
        '''        other = Path(other_db_path)
        if not other.exists():
            return
        src: sqlite3.Connection | None = None
        try:
            src = sqlite3.connect(other)
''',
    )
    value = value.replace(
        '''        finally:
            try:
                src.close()
            except UnboundLocalError:
                pass
''',
        '''        finally:
            if src is not None:
                try:
                    src.close()
                except sqlite3.Error:
                    logger.debug("Failed to close merged source database", exc_info=True)
''',
    )
    write(path, value)


def write_native_checks() -> None:
    value = textwrap.dedent('''\
        # SPDX-License-Identifier: AGPL-3.0-or-later
        """Run mandatory native client validation and emit bounded evidence."""

        from __future__ import annotations

        import argparse
        import hashlib
        import json
        import os
        import platform
        import shutil
        import subprocess  # nosec B404
        import tempfile
        from datetime import datetime, timezone
        from pathlib import Path
        from typing import Any

        MAX_OUTPUT_CHARS = 1000


        def digest(path: Path) -> str:
            value = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    value.update(chunk)
            return value.hexdigest()


        def safe_artifact(root: Path, path: Path) -> tuple[Path | None, str | None]:
            try:
                resolved = path.resolve(strict=True)
            except OSError as exc:
                return None, f"artifact is unavailable: {type(exc).__name__}"
            if not resolved.is_relative_to(root):
                return None, "artifact path escapes the release root"
            if path.is_symlink():
                return None, "artifact path is a symlink"
            return resolved, None


        def run(
            root: Path,
            command: list[str],
            core: str,
            path: Path,
            binary: Path,
        ) -> dict[str, Any]:
            resolved, path_error = safe_artifact(root, path)
            relative = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.name
            base: dict[str, Any] = {
                "core": core,
                "path": relative,
                "status": "failed",
                "command": [Path(command[0]).name, *[relative if item == str(path) else item for item in command[1:]]],
                "artifact_sha256": None,
                "binary_sha256": digest(binary),
                "error": path_error,
            }
            if resolved is None:
                return base
            before = digest(resolved)
            base["artifact_sha256"] = before
            with tempfile.TemporaryDirectory(prefix=f"configstream-{core}-") as home:
                env = {
                    "PATH": os.environ.get("PATH", ""),
                    "HOME": home,
                    "LANG": "C.UTF-8",
                    "LC_ALL": "C.UTF-8",
                    "TZ": "UTC",
                    "NO_COLOR": "1",
                }
                try:
                    result = subprocess.run(  # nosec B603
                        command,
                        capture_output=True,
                        check=False,
                        text=True,
                        timeout=60,
                        cwd=root,
                        env=env,
                    )
                except (OSError, subprocess.TimeoutExpired) as exc:
                    base["error"] = type(exc).__name__
                    return base
            after = digest(resolved)
            if before != after:
                base["error"] = "artifact changed during native validation"
                return base
            output = (result.stderr or result.stdout or "").strip()
            if len(output) > MAX_OUTPUT_CHARS:
                output = output[:MAX_OUTPUT_CHARS] + "...[truncated]"
            base["status"] = "passed" if result.returncode == 0 else "failed"
            base["error"] = None if result.returncode == 0 else output
            return base


        def main() -> int:
            parser = argparse.ArgumentParser(description=__doc__)
            parser.add_argument("artifact_dir", type=Path)
            parser.add_argument("--report", type=Path, required=True)
            args = parser.parse_args()
            root = args.artifact_dir.resolve()
            checks: list[dict[str, Any]] = []
            binary_values = {
                "sing-box": shutil.which("sing-box"),
                "mihomo": shutil.which("mihomo") or shutil.which("clash-meta"),
                "xray": shutil.which("xray"),
            }
            binaries = {
                name: Path(value).resolve() if value else None
                for name, value in binary_values.items()
            }
            for core, binary in binaries.items():
                if binary is None:
                    checks.append(
                        {
                            "core": core,
                            "path": None,
                            "status": "failed",
                            "command": None,
                            "artifact_sha256": None,
                            "binary_sha256": None,
                            "error": "required native validator binary is unavailable",
                        }
                    )
            if binaries["sing-box"]:
                for path in sorted(root.glob("singbox*.json")):
                    checks.append(run(root, [str(binaries["sing-box"]), "check", "-c", str(path)], "sing-box", path, binaries["sing-box"]))
            if binaries["mihomo"]:
                for path in sorted(root.glob("clash*.yaml")):
                    checks.append(run(root, [str(binaries["mihomo"]), "-t", "-f", str(path)], "mihomo", path, binaries["mihomo"]))
            xray_path = root / "xray.json"
            if binaries["xray"] and xray_path.is_file():
                checks.append(run(root, [str(binaries["xray"]), "run", "-test", "-config", str(xray_path)], "xray", xray_path, binaries["xray"]))
            summary = {
                "passed": sum(item["status"] == "passed" for item in checks),
                "failed": sum(item["status"] == "failed" for item in checks),
                "skipped": sum(item["status"] == "skipped" for item in checks),
            }
            report = {
                "schema_version": 2,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_commit": os.environ.get("GITHUB_SHA"),
                "run_id": os.environ.get("GITHUB_RUN_ID"),
                "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
                "platform": {"system": platform.system(), "machine": platform.machine()},
                "tools": {
                    name: {
                        "available": binary is not None,
                        "binary": binary.name if binary else None,
                        "binary_sha256": digest(binary) if binary else None,
                    }
                    for name, binary in binaries.items()
                },
                "checks": checks,
                "summary": summary,
            }
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\\n", encoding="utf-8")
            print(json.dumps(summary))
            return 1 if summary["failed"] or summary["skipped"] or not checks else 0


        if __name__ == "__main__":
            raise SystemExit(main())
        ''')
    write("scripts/native_client_checks.py", value)


def write_release_gate() -> None:
    value = textwrap.dedent('''\
        # SPDX-License-Identifier: AGPL-3.0-or-later
        """Fail closed unless a ConfigStream release is complete and natively validated."""

        from __future__ import annotations

        import argparse
        import hashlib
        import json
        import os
        import shutil
        import uuid
        from datetime import datetime, timezone
        from pathlib import Path, PurePosixPath
        from typing import Any

        from configstream.output.client_formats import validate_xray_config
        from configstream.output.singbox_contract import validate_singbox_config

        REQUIRED_NATIVE_TARGETS = {
            "sing-box": "singbox.json",
            "mihomo": "clash.yaml",
            "xray": "xray.json",
        }
        REQUIRED_FILES = (
            "proxies.json", "metadata.json", "health.json", "artifact_manifest.json",
            "format_compatibility.json", "singbox.json", "clash.yaml", "xray.json",
        )
        TRANSIENT_SUFFIXES = (".lock", ".tmp", ".log", ".pyc", ".pyo", ".swp")
        NATIVE_REPORT_RELATIVE_PATH = "evidence/native_client_check_report.json"
        MAX_FILES = 10000
        MAX_FILE_BYTES = 128 * 1024 * 1024
        MAX_TOTAL_BYTES = 1024 * 1024 * 1024
        MAX_CHECKS = 1000


        def digest(path: Path) -> str:
            value = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    value.update(chunk)
            return value.hexdigest()


        def load_checked(path: Path, errors: list[str]) -> Any:
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    errors.append(f"{path.name} exceeds the control-file size limit")
                    return None
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                errors.append(f"{path.name} is not readable JSON: {type(exc).__name__}")
                return None


        def safe_int(value: Any) -> int:
            return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


        def safe_float(value: Any) -> float:
            return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


        def safe_path(root: Path, relative: str) -> Path:
            if not relative or "\\\\" in relative or "\\x00" in relative:
                raise ValueError(f"unsafe manifest path: {relative!r}")
            pure = PurePosixPath(relative)
            if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
                raise ValueError(f"unsafe manifest path: {relative!r}")
            candidate = root.joinpath(*pure.parts)
            if not candidate.resolve(strict=False).is_relative_to(root.resolve()):
                raise ValueError(f"manifest path escapes artifact root: {relative}")
            return candidate


        def manifest_entries(root: Path) -> list[dict[str, Any]]:
            entries: list[dict[str, Any]] = []
            total = 0
            for path in sorted(root.rglob("*")):
                if path.is_symlink():
                    raise ValueError(f"public artifact contains symlink: {path.relative_to(root).as_posix()}")
                if not path.is_file() or path.name == "artifact_manifest.json":
                    continue
                relative = path.relative_to(root).as_posix()
                if path.name.endswith(TRANSIENT_SUFFIXES):
                    raise ValueError(f"transient file is public: {relative}")
                size = path.stat().st_size
                if size > MAX_FILE_BYTES:
                    raise ValueError(f"public file exceeds size limit: {relative}")
                total += size
                if total > MAX_TOTAL_BYTES:
                    raise ValueError("public artifact exceeds aggregate size limit")
                entries.append({"path": relative, "size_bytes": size, "sha256": digest(path)})
                if len(entries) > MAX_FILES:
                    raise ValueError("public artifact exceeds file-count limit")
            return entries


        def validate_manifest(root: Path, manifest: Any) -> list[str]:
            if not isinstance(manifest, dict):
                return ["artifact manifest must be an object"]
            files = manifest.get("files")
            if not isinstance(files, list):
                return ["artifact manifest files must be a list"]
            if len(files) > MAX_FILES:
                return ["artifact manifest exceeds file-count limit"]
            errors: list[str] = []
            listed: set[str] = set()
            total = 0
            for item in files:
                if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                    errors.append("malformed artifact manifest entry")
                    continue
                relative = item["path"]
                if relative in listed:
                    errors.append(f"duplicate manifest path: {relative}")
                    continue
                listed.add(relative)
                try:
                    path = safe_path(root, relative)
                except ValueError as exc:
                    errors.append(str(exc))
                    continue
                if path.is_symlink():
                    errors.append(f"manifest file is a symlink: {relative}")
                    continue
                if not path.is_file():
                    errors.append(f"manifest file missing: {relative}")
                    continue
                try:
                    size = path.stat().st_size
                    total += size
                    if size > MAX_FILE_BYTES:
                        errors.append(f"manifest file exceeds size limit: {relative}")
                    if item.get("size_bytes") != size:
                        errors.append(f"manifest size mismatch: {relative}")
                    if item.get("sha256") != digest(path):
                        errors.append(f"manifest hash mismatch: {relative}")
                except OSError as exc:
                    errors.append(f"manifest file unreadable: {relative}: {type(exc).__name__}")
            if manifest.get("file_count") not in (None, len(files)):
                errors.append("artifact manifest file_count does not match files")
            if manifest.get("total_size_bytes") not in (None, total):
                errors.append("artifact manifest total_size_bytes does not match files")
            try:
                actual = {item["path"] for item in manifest_entries(root)}
            except (OSError, ValueError) as exc:
                errors.append(str(exc))
                actual = set()
            for relative in sorted(actual - listed):
                errors.append(f"public file omitted from manifest: {relative}")
            return errors


        def validate_native_report(root: Path, report: Any) -> list[str]:
            if not isinstance(report, dict):
                return ["native client report must be an object"]
            errors: list[str] = []
            if report.get("schema_version") != 2:
                errors.append("native client report schema_version must be 2")
            for key, expected in (
                ("source_commit", os.environ.get("GITHUB_SHA")),
                ("run_id", os.environ.get("GITHUB_RUN_ID")),
                ("run_attempt", os.environ.get("GITHUB_RUN_ATTEMPT")),
            ):
                if expected and str(report.get(key) or "") != expected:
                    errors.append(f"native client report provenance mismatch: {key}")
            checks = report.get("checks")
            if not isinstance(checks, list) or not checks:
                return errors + ["native client report has no checks"]
            if len(checks) > MAX_CHECKS:
                return errors + ["native client report exceeds check-count limit"]
            seen: set[tuple[str, str]] = set()
            counts = {"passed": 0, "failed": 0, "skipped": 0}
            for check in checks:
                if not isinstance(check, dict):
                    errors.append("native client report contains malformed check")
                    continue
                core = str(check.get("core") or "")
                relative = check.get("path")
                status = check.get("status")
                if not core or not isinstance(relative, str) or not relative:
                    errors.append("native client report check is missing core/path")
                    continue
                key = (core, relative)
                if key in seen:
                    errors.append(f"duplicate native client check: {core}:{relative}")
                seen.add(key)
                if status in counts:
                    counts[status] += 1
                else:
                    errors.append(f"unknown native validation status: {core}:{relative}={status}")
                if status != "passed":
                    errors.append(f"native validation did not pass: {core}:{relative}={status}")
                try:
                    artifact = safe_path(root, relative)
                except ValueError as exc:
                    errors.append(str(exc))
                    continue
                if not artifact.is_file() or artifact.is_symlink():
                    errors.append(f"native validation references invalid artifact: {core}:{relative}")
                    continue
                expected_digest = check.get("artifact_sha256")
                if not isinstance(expected_digest, str) or len(expected_digest) != 64:
                    errors.append(f"native validation lacks artifact digest: {core}:{relative}")
                elif expected_digest != digest(artifact):
                    errors.append(f"native validation artifact digest mismatch: {core}:{relative}")
            for core, relative in REQUIRED_NATIVE_TARGETS.items():
                if (core, relative) not in seen:
                    errors.append(f"missing required native validation: {core}:{relative}")
            summary = report.get("summary")
            if not isinstance(summary, dict):
                errors.append("native client report has no summary")
            else:
                for key, value in counts.items():
                    if summary.get(key) != value:
                        errors.append(f"native client report summary mismatch: {key}")
            return errors


        def validate(root: Path, native_report: Path, min_coverage: float) -> list[str]:
            errors: list[str] = []
            if not root.is_dir():
                return ["artifact directory does not exist"]
            for name in REQUIRED_FILES:
                path = root / name
                if not path.is_file() or path.is_symlink():
                    errors.append(f"missing or invalid required release file: {name}")
            if not native_report.is_file() or native_report.is_symlink():
                errors.append(f"missing native client report: {native_report.name}")
            if errors:
                return errors
            metadata = load_checked(root / "metadata.json", errors)
            health = load_checked(root / "health.json", errors)
            manifest = load_checked(root / "artifact_manifest.json", errors)
            records = load_checked(root / "proxies.json", errors)
            compatibility = load_checked(root / "format_compatibility.json", errors)
            report = load_checked(native_report, errors)
            xray = load_checked(root / "xray.json", errors)
            singbox = load_checked(root / "singbox.json", errors)
            if errors:
                return errors
            if not isinstance(records, list) or not records:
                errors.append("proxies.json must contain at least one public record")
            if not isinstance(metadata, dict):
                errors.append("metadata.json must be an object")
                metadata = {}
            coverage = safe_float(metadata.get("source_coverage"))
            if coverage < min_coverage:
                errors.append(f"source coverage {coverage:.4f} is below {min_coverage:.4f}")
            if metadata.get("time_limited") is True:
                errors.append("pipeline was time-limited")
            if safe_int(metadata.get("logical_total_working") or metadata.get("total_working")) <= 0:
                errors.append("no logical working proxies")
            candidates = safe_int(metadata.get("shielded_candidate_count") or metadata.get("shielded_count"))
            verified = safe_int(metadata.get("shielded_verified_count"))
            if candidates > verified:
                errors.append(f"{candidates - verified} shielded candidates are unverified")
            drop_reasons = metadata.get("drop_reasons")
            if drop_reasons is not None and not isinstance(drop_reasons, dict):
                errors.append("metadata drop_reasons must be an object")
            elif isinstance(drop_reasons, dict):
                for key, value in drop_reasons.items():
                    lowered = str(key).lower()
                    if any(marker in lowered for marker in ("nonetype", "sequence item", "tester")) and safe_int(value):
                        errors.append(f"tester infrastructure errors remain: {key}={value}")
            if not isinstance(health, dict):
                errors.append("health.json must be an object")
            else:
                blockers = health.get("release_blockers", [])
                if not isinstance(blockers, list):
                    errors.append("health release_blockers must be a list")
                else:
                    errors.extend(f"health blocker: {item}" for item in blockers)
            if not isinstance(compatibility, dict):
                errors.append("format_compatibility.json must be an object")
            else:
                targets = compatibility.get("targets")
                if not isinstance(targets, dict):
                    errors.append("compatibility targets must be an object")
                else:
                    for target in REQUIRED_NATIVE_TARGETS:
                        item = targets.get(target)
                        if not isinstance(item, dict) or item.get("status") not in {"generated", "passed"}:
                            errors.append(f"compatibility target is not generated: {target}")
            errors.extend(validate_native_report(root, report))
            try:
                errors.extend(validate_xray_config(xray, "xray.json"))
            except (TypeError, ValueError, KeyError) as exc:
                errors.append(f"xray validation failed safely: {type(exc).__name__}")
            try:
                errors.extend(validate_singbox_config(singbox, "singbox.json"))
            except (TypeError, ValueError, KeyError) as exc:
                errors.append(f"sing-box validation failed safely: {type(exc).__name__}")
            errors.extend(validate_manifest(root, manifest))
            return errors


        def promote(root: Path, native_report: Path, min_coverage: float) -> None:
            manifest = load_checked(root / "artifact_manifest.json", [])
            had_signature = isinstance(manifest, dict) and "manifest_signature" in manifest
            signing_key = os.environ.get("CS_SIGNING_PRIVATE_KEY_HEX")
            if had_signature and not signing_key:
                raise ValueError("promotion would invalidate manifest_signature but no signing key is configured")
            stage = root.parent / f".{root.name}.promote-{uuid.uuid4().hex}"
            backup = root.parent / f".{root.name}.backup-{uuid.uuid4().hex}"
            shutil.copytree(root, stage, symlinks=True)
            try:
                evidence = stage / NATIVE_REPORT_RELATIVE_PATH
                evidence.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(native_report, evidence)
                metadata = load_checked(stage / "metadata.json", [])
                health = load_checked(stage / "health.json", [])
                staged_manifest = load_checked(stage / "artifact_manifest.json", [])
                if not isinstance(metadata, dict) or not isinstance(health, dict):
                    raise ValueError("metadata.json and health.json must be objects")
                health.update({
                    "schema_version": "2.0",
                    "status": "ok",
                    "total_working": safe_int(metadata.get("logical_total_working") or metadata.get("total_working")),
                    "total_tested": safe_int(metadata.get("total_tested") or metadata.get("tested")),
                    "source_coverage": safe_float(metadata.get("source_coverage")),
                    "schema_validated": True,
                    "native_clients_validated": True,
                    "release_blockers": [],
                    "native_report": NATIVE_REPORT_RELATIVE_PATH,
                    "native_report_sha256": digest(evidence),
                })
                (stage / "health.json").write_text(json.dumps(health, indent=2, ensure_ascii=False) + "\\n", encoding="utf-8")
                entries = manifest_entries(stage)
                if not isinstance(staged_manifest, dict):
                    staged_manifest = {}
                staged_manifest.pop("manifest_signature", None)
                staged_manifest.update({
                    "schema_version": "2.0",
                    "generated_at": staged_manifest.get("generated_at") or datetime.now(timezone.utc).isoformat(),
                    "source_commit": os.environ.get("GITHUB_SHA", str(staged_manifest.get("source_commit") or "")),
                    "run_id": os.environ.get("GITHUB_RUN_ID", str(staged_manifest.get("run_id") or "")),
                    "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", str(staged_manifest.get("run_attempt") or "")),
                    "file_count": len(entries),
                    "total_size_bytes": sum(int(item["size_bytes"]) for item in entries),
                    "files": entries,
                })
                if signing_key:
                    from configstream.signer import Signer
                    staged_manifest["manifest_signature"] = Signer(signing_key).sign_manifest(staged_manifest)
                (stage / "artifact_manifest.json").write_text(json.dumps(staged_manifest, indent=2, ensure_ascii=False) + "\\n", encoding="utf-8")
                errors = validate(stage, evidence, min_coverage)
                if errors:
                    raise ValueError("post-promotion validation failed: " + "; ".join(errors))
                os.replace(root, backup)
                try:
                    os.replace(stage, root)
                except OSError:
                    os.replace(backup, root)
                    raise
                shutil.rmtree(backup)
            finally:
                if stage.exists():
                    shutil.rmtree(stage, ignore_errors=True)


        def main() -> int:
            parser = argparse.ArgumentParser(description=__doc__)
            parser.add_argument("artifact_dir", type=Path)
            parser.add_argument("--native-report", type=Path, required=True)
            parser.add_argument("--min-source-coverage", type=float, default=0.80)
            parser.add_argument("--promote", action="store_true")
            args = parser.parse_args()
            root = args.artifact_dir.resolve()
            native_report = args.native_report.resolve()
            try:
                errors = validate(root, native_report, args.min_source_coverage)
            except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError) as exc:
                errors = [f"release validation failed safely: {type(exc).__name__}"]
            if errors:
                print("ERROR: release gate failed")
                for error in errors:
                    print(f"  - {error}")
                return 1
            if args.promote:
                try:
                    promote(root, native_report, args.min_source_coverage)
                except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError) as exc:
                    print(f"ERROR: release promotion failed: {type(exc).__name__}: {exc}")
                    return 1
            print("OK: release gate passed")
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        ''')
    write("scripts/release_gate.py", value)


def main() -> int:
    patch_workflows()
    patch_publication()
    patch_finalize_release()
    patch_client_formats()
    patch_small_current_findings()
    patch_storage()
    write_native_checks()
    write_release_gate()
    print("Applied PR 531 final remediation set")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
