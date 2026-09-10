# SPDX-License-Identifier: AGPL-3.0-or-later
"""One-shot exact-anchor remediation helper for PR #593; removes itself after use."""
from pathlib import Path


def replace(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if old not in text:
        if new in text:
            return
        raise SystemExit(f"anchor not found in {path}: {old[:100]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


# Optional MaxMind dependency must remain lazy for unrelated CLI commands.
replace(
    "src/configstream/cli.py",
    "import httpx\nimport maxminddb\nfrom rich.console",
    "import httpx\nfrom rich.console",
)
replace(
    "src/configstream/cli.py",
    '''    try:\n        import geoip2.database\n\n        if not path.is_file() or path.stat().st_size <= 0:\n            return False\n        with geoip2.database.Reader(path) as reader:\n            database_type = reader.metadata().database_type\n        return expected_type in database_type\n    except (\n        ImportError,\n        OSError,\n        ValueError,\n        TypeError,\n        maxminddb.InvalidDatabaseError,\n    ) as exc:\n''',
    '''    try:\n        import geoip2.database\n        from maxminddb import InvalidDatabaseError\n    except ImportError as exc:\n        logging.getLogger(__name__).warning(\n            "GeoIP database validation unavailable for %s: %s",\n            path,\n            type(exc).__name__,\n        )\n        return False\n\n    try:\n        if not path.is_file() or path.stat().st_size <= 0:\n            return False\n        with geoip2.database.Reader(path) as reader:\n            database_type = reader.metadata().database_type\n        return expected_type in database_type\n    except (OSError, ValueError, TypeError, InvalidDatabaseError) as exc:\n''',
)

# Detect common Bash grammar, not merely a marker list.
replace(
    "scripts/validate_workflows.py",
    '''def _is_bash_shell(value: object) -> bool:\n''',
    '''_BASH_ARRAY_ASSIGNMENT_RE = re.compile(\n    r"(?m)(?:^|[;\\n])\\s*[A-Za-z_][A-Za-z0-9_]*\\s*=\\s*\\([^\\n)]*\\)"\n)\n_BASH_ARITHMETIC_COMMAND_RE = re.compile(\n    r"(?m)(?:^|[;|&\\n])\\s*\\(\\([^\\n]+\\)\\)"\n)\n_BASH_REGEX_CONDITIONAL_RE = re.compile(r"\\[\\[[^\\n]*=~[^\\n]*\\]\\]")\n\n\ndef _uses_bash_only_syntax(command: str) -> bool:\n    if any(marker in command for marker in _BASH_ONLY_RUN_MARKERS):\n        return True\n    return any(\n        pattern.search(command)\n        for pattern in (\n            _BASH_ARRAY_ASSIGNMENT_RE,\n            _BASH_ARITHMETIC_COMMAND_RE,\n            _BASH_REGEX_CONDITIONAL_RE,\n        )\n    )\n\n\ndef _is_bash_shell(value: object) -> bool:\n''',
)
replace(
    "scripts/validate_workflows.py",
    '''            if not command or not any(\n                marker in command for marker in _BASH_ONLY_RUN_MARKERS\n            ):\n                continue\n''',
    '''            if not command or not _uses_bash_only_syntax(command):\n                continue\n''',
)

# Derive verifier Go toolchain from the governed runtime manifest.
replace(
    "scripts/verify_repository.py",
    '''def build_plan(profile: str) -> list[Stage]:\n    python = sys.executable\n    go_environment = (("GOTOOLCHAIN", "go1.24.3"),)\n''',
    '''def _go_runtime_contract(root: Path = Path(".")) -> tuple[str, tuple[int, ...]]:\n    manifest = json.loads(\n        (root / "config/runtime-versions.json").read_text(encoding="utf-8")\n    )\n    go = manifest.get("go")\n    if not isinstance(go, dict):\n        raise ValueError("runtime-versions.json has no Go runtime contract")\n    toolchain = str(go.get("toolchain") or "")\n    language = str(go.get("language") or "")\n    if not re.fullmatch(r"\\d+\\.\\d+\\.\\d+", toolchain) or not re.fullmatch(\n        r"\\d+\\.\\d+\\.\\d+", language\n    ):\n        raise ValueError("runtime-versions.json has invalid Go runtime versions")\n    return f"go{toolchain}", tuple(int(part) for part in language.split("."))\n\n\ndef build_plan(profile: str) -> list[Stage]:\n    python = sys.executable\n    governed_go_toolchain, governed_go_minimum = _go_runtime_contract()\n    go_environment = (("GOTOOLCHAIN", governed_go_toolchain),)\n''',
)
verifier = Path("scripts/verify_repository.py")
text = verifier.read_text(encoding="utf-8")
text = text.replace(
    "minimum_tool_version=(1, 24, 0),", "minimum_tool_version=governed_go_minimum,"
)
text = text.replace(
    "minimum_tool_version=(1, 24, 3),", "minimum_tool_version=governed_go_minimum,"
)
verifier.write_text(text, encoding="utf-8")

# Keep filesystem probes inside their existing semantic error boundaries.
replace(
    "src/configstream/anomaly.py",
    '''        if not other_db_path.exists():\n            return\n        if other_db_path.stat().st_size > MAX_MERGE_DB_BYTES:\n            logger.error("Refusing oversized anomaly database merge: %s", other_db_path)\n            return\n\n        try:\n            with self._lock:\n''',
    '''        try:\n            if not other_db_path.exists():\n                return\n            if other_db_path.stat().st_size > MAX_MERGE_DB_BYTES:\n                logger.error("Refusing oversized anomaly database merge: %s", other_db_path)\n                return\n\n            with self._lock:\n''',
)
replace(
    "src/configstream/quality/storage.py",
    '''        other = Path(other_db_path)\n        if not other.exists():\n            return\n        if other.stat().st_size > MAX_MERGE_DB_BYTES:\n            raise QualityStorageError("refusing oversized source quality database")\n        src: Optional[sqlite3.Connection] = None\n        try:\n            src = sqlite3.connect(other, timeout=20)\n''',
    '''        other = Path(other_db_path)\n        src: Optional[sqlite3.Connection] = None\n        try:\n            if not other.exists():\n                return\n            if other.stat().st_size > MAX_MERGE_DB_BYTES:\n                raise QualityStorageError("refusing oversized source quality database")\n            src = sqlite3.connect(other, timeout=20)\n''',
)

# Restore setup I/O belongs inside the existing fail-closed restore boundary.
replace(
    "src/configstream/backup.py",
    '''    target_file.parent.mkdir(parents=True, exist_ok=True)\n    fd, temp_name = tempfile.mkstemp(\n        prefix=f".{target_file.name}.restore-", dir=target_file.parent\n    )\n    os.close(fd)\n    temp_path = Path(temp_name)\n\n    try:\n        opener = gzip.open if backup_file.name.endswith(".gz") else open\n''',
    '''    temp_path: Path | None = None\n    try:\n        target_file.parent.mkdir(parents=True, exist_ok=True)\n        fd, temp_name = tempfile.mkstemp(\n            prefix=f".{target_file.name}.restore-", dir=target_file.parent\n        )\n        os.close(fd)\n        temp_path = Path(temp_name)\n\n        opener = gzip.open if backup_file.name.endswith(".gz") else open\n''',
)
replace(
    "src/configstream/backup.py",
    '''        try:\n            temp_path.unlink(missing_ok=True)\n        except OSError as cleanup_exc:\n            logger.debug(\n                "Failed to remove restore temp file %s: %s",\n                temp_path.name,\n                safe_log_text(cleanup_exc),\n            )\n''',
    '''        if temp_path is not None:\n            try:\n                temp_path.unlink(missing_ok=True)\n            except OSError as cleanup_exc:\n                logger.debug(\n                    "Failed to remove restore temp file %s: %s",\n                    temp_path.name,\n                    safe_log_text(cleanup_exc),\n                )\n''',
)

# Slipstream support is optional; unsupported platforms must not break TUI startup.
replace(
    "src/configstream/tools/dns_scanner/python/dnsscanner_tui.py",
    '''    def get_platform_key(self) -> str:\n        """Return an architecture-specific key present in the pinned manifest."""\n        key = f"{self.system}-{self.machine}"\n        if key not in self.ARTIFACTS:\n            raise RuntimeError(f"Unsupported platform: {self.system} {self.machine}")\n        return key\n''',
    '''    def is_supported(self) -> bool:\n        """Return whether this platform has a pinned Slipstream artifact."""\n        return f"{self.system}-{self.machine}" in self.ARTIFACTS\n\n    def get_platform_key(self) -> str:\n        """Return an architecture-specific key present in the pinned manifest."""\n        key = f"{self.system}-{self.machine}"\n        if key not in self.ARTIFACTS:\n            raise RuntimeError(f"Unsupported platform: {self.system} {self.machine}")\n        return key\n''',
)
replace(
    "src/configstream/tools/dns_scanner/python/dnsscanner_tui.py",
    '''        self.slipstream_manager = SlipstreamManager()\n        self.slipstream_path = str(self.slipstream_manager.get_executable_path())\n        self.slipstream_domain = ""\n''',
    '''        self.slipstream_manager = SlipstreamManager()\n        self.slipstream_path = ""\n        self.slipstream_domain = ""\n''',
)
replace(
    "src/configstream/tools/dns_scanner/python/dnsscanner_tui.py",
    '''        # Check if slipstream needs to be downloaded\n        if self.test_slipstream and not self.slipstream_manager.is_installed():\n''',
    '''        # Resolve Slipstream only when the optional feature is requested.\n        if self.test_slipstream and not self.slipstream_manager.is_supported():\n            self.notify(\n                f"Slipstream is unsupported on {self.slipstream_manager.system} {self.slipstream_manager.machine}",\n                severity="error",\n            )\n            return\n        if self.test_slipstream and self.slipstream_manager.is_installed():\n            self.slipstream_path = str(self.slipstream_manager.get_executable_path())\n        if self.test_slipstream and not self.slipstream_manager.is_installed():\n''',
)

# Artifact status recording must survive a missing matrix and validate exact shard identities.
replace(
    ".github/workflows/main.yml",
    '''          shard_status="${{ steps.shard_download.outcome }}"\n          if [ "$shard_status" = success ]; then\n            if ! python - <<'PYCODE'\n          import json\n          from pathlib import Path\n\n          matrix = json.loads(Path("matrix-artifact/source-matrix.json").read_text(encoding="utf-8"))\n          expected = sum(1 for row in matrix.get("include", []) if row.get("enabled", True))\n          lineage = list(Path("artifacts").rglob("shard_lineage.json"))\n          if expected <= 0 or len(lineage) != expected:\n              raise SystemExit(\n                  f"shard artifact lineage mismatch: expected {expected}, found {len(lineage)}"\n              )\n          PYCODE\n            then\n              shard_status=failure\n            fi\n          fi\n''',
    '''          shard_status="${{ steps.shard_download.outcome }}"\n          matrix_download_status="${{ steps.matrix_artifact_download.outcome }}"\n          if [ "$shard_status" = success ]; then\n            if [ "$matrix_download_status" != success ] || [ ! -s matrix-artifact/source-matrix.json ]; then\n              echo "::error::Shard validation cannot run without the exact source matrix artifact"\n              shard_status=failure\n            elif ! python - <<'PYCODE'\n          import json\n          from collections import Counter\n          from pathlib import Path\n\n          matrix = json.loads(Path("matrix-artifact/source-matrix.json").read_text(encoding="utf-8"))\n          rows = [row for row in matrix.get("include", []) if row.get("enabled", True)]\n          expected = {\n              (str(row.get("batch")), int(row.get("part")), str(row.get("source_file")), str(row.get("source_sha256")))\n              for row in rows\n          }\n          if not expected or len(expected) != len(rows):\n              raise SystemExit("source matrix contains empty or duplicate shard identities")\n\n          observed = []\n          for path in Path("artifacts").rglob("shard_lineage.json"):\n              payload = json.loads(path.read_text(encoding="utf-8"))\n              observed.append(\n                  (\n                      str(payload.get("batch")),\n                      int(payload.get("part")),\n                      str(payload.get("source_file")),\n                      str(payload.get("source_sha256")),\n                  )\n              )\n          counts = Counter(observed)\n          observed_set = set(observed)\n          missing = sorted(expected - observed_set)\n          unexpected = sorted(observed_set - expected)\n          duplicates = sorted(identity for identity, count in counts.items() if count != 1)\n          if missing or unexpected or duplicates or len(observed) != len(expected):\n              raise SystemExit(\n                  "shard artifact lineage mismatch: "\n                  f"expected={len(expected)} found={len(observed)} "\n                  f"missing={missing[:3]} unexpected={unexpected[:3]} duplicates={duplicates[:3]}"\n              )\n          PYCODE\n            then\n              shard_status=failure\n            fi\n          fi\n''',
)
