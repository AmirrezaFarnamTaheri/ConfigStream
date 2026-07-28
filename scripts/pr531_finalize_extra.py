#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Apply the expanded Qodo/CodeRabbit remediation set for PR 531."""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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


def patch_evidence() -> None:
    policy = textwrap.dedent('''\
        # SPDX-License-Identifier: AGPL-3.0-or-later
        """Publication-channel eligibility policy."""

        from __future__ import annotations

        from dataclasses import dataclass
        from datetime import datetime, timezone
        from typing import Iterable

        from .models import PublicationChannel, ValidationEvidence, ValidationOutcome
        from .scoring import score_evidence


        @dataclass(frozen=True)
        class EligibilityDecision:
            eligible: bool
            channel: PublicationChannel
            confidence: float
            reasons: tuple[str, ...]


        def evaluate_eligibility(
            evidence: Iterable[ValidationEvidence],
            *,
            channel: PublicationChannel,
            now: datetime | None = None,
            historical_success_ratio: float = 0.0,
            longitudinal_stability: float = 0.0,
            source_prior: float = 0.0,
        ) -> EligibilityDecision:
            items = tuple(evidence)
            current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
            current_items = tuple(item for item in items if current < item.expires_at)
            active = tuple(
                item
                for item in current_items
                if item.outcome is ValidationOutcome.PASSED
            )
            reasons: list[str] = []

            if not active:
                reasons.append("no_current_passing_evidence")

            # Expired historical failures are retained for audit/scoring history but
            # cannot permanently poison a fresh decision. Current failed or unsafe
            # observations remain visible to operators and block eligibility.
            for item in current_items:
                if not item.public_address_validated:
                    reasons.append("address_not_proven_global")
                if not item.dns_rebinding_guarded:
                    reasons.append("dns_rebinding_not_guarded")
                if not item.protocol_confirmed:
                    reasons.append("protocol_not_confirmed")
                if item.interception_detected is True:
                    reasons.append("tls_interception_detected")
                if item.content_integrity_valid is False:
                    reasons.append("content_integrity_failed")
                if item.critical_reputation_flags:
                    reasons.append("critical_reputation_flag")

            vantages = {item.network_vantage_id for item in active}
            required_vantages = 1 if channel is PublicationChannel.EXPERIMENTAL else 2
            if len(vantages) < required_vantages:
                reasons.append("insufficient_independent_vantages")

            if channel is PublicationChannel.STABLE:
                if len(active) < 3:
                    reasons.append("insufficient_recent_successes")
                if historical_success_ratio < 0.60:
                    reasons.append("historical_success_below_threshold")
                if longitudinal_stability < 0.50:
                    reasons.append("longitudinal_stability_below_threshold")

            confidence = score_evidence(
                items,
                now=current,
                historical_success_ratio=historical_success_ratio,
                longitudinal_stability=longitudinal_stability,
                source_prior=source_prior,
            )
            threshold = 0.55 if channel is PublicationChannel.EXPERIMENTAL else 0.80
            if confidence < threshold:
                reasons.append("confidence_below_threshold")

            unique_reasons = tuple(sorted(set(reasons)))
            return EligibilityDecision(
                eligible=not unique_reasons,
                channel=channel,
                confidence=confidence,
                reasons=unique_reasons,
            )
        ''')
    scoring = textwrap.dedent('''\
        # SPDX-License-Identifier: AGPL-3.0-or-later
        """Deterministic confidence scoring for validation evidence."""

        from __future__ import annotations

        from datetime import datetime, timedelta, timezone
        from typing import Iterable

        from configstream.signer import CLOCK_SKEW_TOLERANCE_SECONDS

        from .models import ValidationEvidence, ValidationOutcome


        def _clamp(value: float) -> float:
            return max(0.0, min(1.0, float(value)))


        def score_evidence(
            evidence: Iterable[ValidationEvidence],
            *,
            now: datetime | None = None,
            historical_success_ratio: float = 0.0,
            longitudinal_stability: float = 0.0,
            source_prior: float = 0.0,
        ) -> float:
            """Score current independent evidence without unsafe compensation."""

            items = tuple(evidence)
            if not items:
                return 0.0
            current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
            future_limit = current + timedelta(seconds=CLOCK_SKEW_TOLERANCE_SECONDS)
            current_items = tuple(
                item
                for item in items
                if current < item.expires_at and item.tested_at <= future_limit
            )
            if not current_items:
                return 0.0

            active = tuple(
                item
                for item in current_items
                if item.outcome is ValidationOutcome.PASSED
                and item.public_address_validated
                and item.dns_rebinding_guarded
                and item.protocol_confirmed
                and item.interception_detected is not True
                and item.content_integrity_valid is not False
                and not item.critical_reputation_flags
            )
            if not active:
                return 0.0

            freshest_age = max(
                0.0,
                min((current - item.tested_at).total_seconds() for item in active),
            )
            freshness = _clamp(1.0 - freshest_age / 3600.0)
            recent_success_ratio = len(active) / len(current_items)
            vantage_diversity = _clamp(
                len({item.network_vantage_id for item in active}) / 2.0
            )
            protocol_certainty = sum(
                item.protocol_confirmed for item in current_items
            ) / len(current_items)
            integrity = sum(
                item.content_integrity_valid is not False
                and item.interception_detected is not True
                for item in current_items
            ) / len(current_items)
            reputation = sum(
                not item.critical_reputation_flags for item in current_items
            ) / len(current_items)

            score = (
                0.20 * freshness
                + 0.20 * _clamp(recent_success_ratio)
                + 0.15 * _clamp(longitudinal_stability)
                + 0.15 * _clamp(integrity)
                + 0.10 * _clamp(protocol_certainty)
                + 0.10 * vantage_diversity
                + 0.05 * _clamp(source_prior)
                + 0.05 * _clamp(reputation)
            )
            score += 0.05 * (_clamp(historical_success_ratio) - 0.5)
            return round(_clamp(score), 6)
        ''')
    write("src/configstream/evidence/policy.py", policy)
    write("src/configstream/evidence/scoring.py", scoring)

    replace(
        "src/configstream/evidence/models.py",
        '''        validity_seconds = (self.expires_at - self.tested_at).total_seconds()
        if validity_seconds > MAX_EVIDENCE_TTL_SECONDS:
            raise ValueError("evidence validity window exceeds the maximum TTL")
        if self.outcome is ValidationOutcome.PASSED:
''',
        '''        validity_seconds = (self.expires_at - self.tested_at).total_seconds()
        if validity_seconds > MAX_EVIDENCE_TTL_SECONDS:
            raise ValueError("evidence validity window exceeds the maximum TTL")
        if self.selected_address is not None:
            try:
                ip_address(self.selected_address)
            except ValueError as exc:
                raise ValueError("selected_address must be a valid IP address") from exc
        if self.egress_ip is not None:
            try:
                ip_address(self.egress_ip)
            except ValueError as exc:
                raise ValueError("egress_ip must be a valid IP address") from exc
        if self.public_address_validated and (
            self.selected_address is None
            or self.selected_address not in self.resolved_addresses
        ):
            raise ValueError(
                "validated public evidence must select a resolved address"
            )
        if self.outcome is ValidationOutcome.PASSED:
''',
    )


def patch_output_contracts() -> None:
    path = "src/configstream/output/singbox_contract.py"
    value = read(path)
    value = value.replace("from typing import Any", "from typing import Any, Dict, List, Set, Tuple")
    value = re.sub(r"\bdict\[str, Any\]", "Dict[str, Any]", value)
    value = re.sub(r"\blist\[str\]", "List[str]", value)
    value = re.sub(r"\blist\[Dict\[str, Any\]\]", "List[Dict[str, Any]]", value)
    value = re.sub(r"\bset\[str\]", "Set[str]", value)
    value = re.sub(
        r"tuple\[List\[Dict\[str, Any\]\], List\[Dict\[str, Any\]\], Set\[str\]\]",
        "Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Set[str]]",
        value,
    )
    write(path, value)

    path = "scripts/finalize_release_outputs.py"
    value = read(path)
    value, matches = re.subn(
        r"\n\ndef _xray_outbound\(.*?\n\ndef _repair_clash\(",
        "\n\ndef _repair_clash(",
        value,
        count=1,
        flags=re.DOTALL,
    )
    if matches != 1:
        raise RuntimeError("could not remove duplicate local Xray helpers")
    old = '''    known = set(tags)
    for outbound in outbounds:
        if outbound.get("type") not in {"selector", "urltest"}:
            continue
        members = outbound.get("outbounds")
        if not isinstance(members, list):
            continue
        unique: list[str] = []
        for member in members:
            tag = str(member)
            if tag in known and tag not in unique:
                unique.append(tag)
            if len(unique) >= MAX_SELECTOR_MEMBERS:
                break
        if not unique and "direct" in known:
            unique = ["direct"]
        outbound["outbounds"] = unique
        if outbound.get("default") not in unique:
            outbound.pop("default", None)
'''
    new = '''    known = set(tags)
    retained_outbounds: list[dict[str, Any]] = []
    for outbound in outbounds:
        if outbound.get("type") not in {"selector", "urltest"}:
            retained_outbounds.append(outbound)
            continue
        members = outbound.get("outbounds")
        if not isinstance(members, list):
            continue
        unique: list[str] = []
        for member in members:
            tag = str(member)
            if tag in known and tag not in unique:
                unique.append(tag)
            if len(unique) >= MAX_SELECTOR_MEMBERS:
                break
        if not unique and "direct" in known:
            unique = ["direct"]
        if not unique:
            continue
        outbound["outbounds"] = unique
        if outbound.get("default") not in unique:
            outbound.pop("default", None)
        retained_outbounds.append(outbound)
    config["outbounds"] = retained_outbounds
'''
    if old not in value:
        raise RuntimeError("selector normalization pattern changed")
    write(path, value.replace(old, new))


def patch_network_and_runtime() -> None:
    replace(
        "src/configstream/sources/adapters/github_blob.py",
        '''            follow_redirects=False,
            headers={"Accept": "text/plain, application/octet-stream"},
        ) as response:
''',
        '''            follow_redirects=False,
            headers={"Accept": "text/plain, application/octet-stream"},
            timeout=httpx.Timeout(20.0, connect=10.0, read=15.0, write=10.0),
        ) as response:
''',
    )
    replace(
        "src/configstream/sources/adapters/github_blob.py",
        '''            content = b"".join(
                [
                    chunk
                    async for chunk in self._bounded_chunks(
                        response,
                        max_bytes=self.provider.max_response_bytes,
                    )
                ]
            )
''',
        '''            content_buffer = bytearray()
            async for chunk in self._bounded_chunks(
                response,
                max_bytes=self.provider.max_response_bytes,
            ):
                content_buffer.extend(chunk)
            content = bytes(content_buffer)
''',
    )

    replace(
        "src/configstream/output_transport.py",
        "import os\n",
        "",
        required=False,
    )
    replace(
        "src/configstream/output_transport.py",
        '''        temporary = gz_path.with_suffix(gz_path.suffix + ".tmp")
        try:
            with gzip.open(temporary, "wt", encoding="utf-8") as handle:
                handle.write(json_content)
            os.replace(temporary, gz_path)
        except Exception as exc:
            logger.error("Gzip compression failed for %s: %s", path, exc)
            temporary.unlink(missing_ok=True)
            raise
''',
        '''        try:
            compressed = gzip.compress(json_content.encode("utf-8"), mtime=0)
            AtomicFileWriter.write_bytes(gz_path, compressed)
        except Exception as exc:
            logger.error("Gzip compression failed for %s: %s", path, exc)
            raise
''',
    )

    replace(
        "src/configstream/pipeline/producer.py",
        '''        for _ in range(num_consumers):
            while True:
''',
        '''        loop = asyncio.get_running_loop()
        sentinel_deadline = loop.time() + max(5.0, float(settings.SHUTDOWN_GRACE_SECONDS))
        for _ in range(num_consumers):
            while True:
''',
    )
    replace(
        "src/configstream/pipeline/producer.py",
        '''                    except asyncio.TimeoutError:
                        logger.debug(
                            "Sentinel enqueue still blocked after 5s; retrying "
                            "(consumers are expected to be draining)."
                        )
                        continue
''',
        '''                    except asyncio.TimeoutError:
                        if loop.time() >= sentinel_deadline:
                            logger.error(
                                "Sentinel delivery deadline exceeded; abandoning "
                                "remaining marker after consumer failure or stall."
                            )
                            break
                        logger.debug(
                            "Sentinel enqueue still blocked after 5s; retrying "
                            "within the bounded shutdown deadline."
                        )
                        continue
''',
    )

    replace(
        "src/configstream/server/routes/lab.py",
        '''    budget[0] -= 1
    if budget[0] < 0:
        raise HTTPException(
            status_code=400,
            detail="Config contains too many outbound nodes for live lab testing",
        )
    if not isinstance(outbound, dict):
        raise HTTPException(status_code=400, detail=f"{path} must be an object")
''',
        '''    if not isinstance(outbound, dict):
        raise HTTPException(status_code=400, detail=f"{path} must be an object")
    budget[0] -= 1
    if budget[0] < 0:
        raise HTTPException(
            status_code=400,
            detail="Config contains too many outbound nodes for live lab testing",
        )
''',
    )
    replace(
        "src/configstream/server/routes/lab.py",
        "    clean_config = await _validate_and_build_lab_config(config)",
        '''    try:
        async with asyncio.timeout(settings.LAB_TEST_TIMEOUT_SECONDS):
            clean_config = await _validate_and_build_lab_config(config)
    except TimeoutError as exc:
        raise HTTPException(
            status_code=408,
            detail="Lab configuration validation exceeded the request deadline",
        ) from exc''',
    )

    replace(
        "src/configstream/testers/go_tester/manager.py",
        '''    if not math.isfinite(latency):
        return None
    return latency
''',
        '''    if not math.isfinite(latency) or latency < 0:
        return None
    return latency
''',
    )


def patch_storage_after_primary() -> None:
    path = "src/configstream/quality/storage.py"
    value = read(path)
    value = value.replace("SCHEMA_VERSION = 3", "SCHEMA_VERSION = 4")
    value = value.replace(
        '''                        trust_score REAL NOT NULL DEFAULT 50.0,
                        status TEXT NOT NULL DEFAULT 'active'
''',
        '''                        trust_score REAL NOT NULL DEFAULT 50.0,
                        status TEXT NOT NULL DEFAULT 'active',
                        state_sequence INTEGER NOT NULL DEFAULT 0
''',
    )
    value = value.replace(
        '''                if "status" not in source_columns:
                    conn.execute(
                        "ALTER TABLE source_stats ADD COLUMN status TEXT NOT NULL DEFAULT 'active'"
                    )

                conn.execute("""
''',
        '''                if "status" not in source_columns:
                    conn.execute(
                        "ALTER TABLE source_stats ADD COLUMN status TEXT NOT NULL DEFAULT 'active'"
                    )
                if "state_sequence" not in source_columns:
                    conn.execute(
                        "ALTER TABLE source_stats ADD COLUMN state_sequence INTEGER NOT NULL DEFAULT 0"
                    )

                conn.execute("""
''',
    )
    value = value.replace(
        '''                conn.execute("""
                    CREATE TABLE IF NOT EXISTS source_stats (
''',
        '''                stored_version = conn.execute(
                    "SELECT value FROM schema_meta WHERE key = 'schema_version'"
                ).fetchone()
                if stored_version is not None and int(stored_version[0]) > SCHEMA_VERSION:
                    raise QualityStorageError(
                        "quality database schema is newer than this application"
                    )

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS source_stats (
''',
        1,
    )
    value = value.replace(
        '''            "status": "active",
        }
''',
        '''            "status": "active",
            "state_sequence": 0,
        }
''',
        1,
    )
    value = value.replace(
        '''                           trust_score, status
                    FROM source_stats WHERE url = ?
''',
        '''                           trust_score, status, state_sequence
                    FROM source_stats WHERE url = ?
''',
        1,
    )
    value = value.replace(
        '''                        "status": existing[7],
                    }
                    merged = {**current, **stats}
''',
        '''                        "status": existing[7],
                        "state_sequence": existing[8],
                    }
                    merged = {**current, **stats}
                    merged["state_sequence"] = max(
                        int(current["state_sequence"]) + 1,
                        int(stats.get("state_sequence", 0)),
                    )
''',
        1,
    )
    value = value.replace(
        '''                else:
                    merged = {**defaults, **stats}

                conn.execute(
''',
        '''                else:
                    merged = {**defaults, **stats}
                    merged["state_sequence"] = max(
                        1, int(stats.get("state_sequence", 0))
                    )

                conn.execute(
''',
        1,
    )
    value = value.replace(
        '''                        trust_score, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
''',
        '''                        trust_score, status, state_sequence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''',
        1,
    )
    value = value.replace(
        '''                        trust_score=excluded.trust_score,
                        status=excluded.status
''',
        '''                        trust_score=excluded.trust_score,
                        status=excluded.status,
                        state_sequence=excluded.state_sequence
''',
        1,
    )
    value = value.replace(
        '''                        str(merged["status"]),
                    ),
''',
        '''                        str(merged["status"]),
                        int(merged["state_sequence"]),
                    ),
''',
        1,
    )
    value = value.replace(
        'source_rows = src.execute("SELECT * FROM source_stats").fetchall()',
        'source_rows = src.execute("SELECT * FROM source_stats")',
    )
    value = value.replace(
        'run_rows = src.execute("SELECT * FROM source_runs").fetchall()',
        'run_rows = src.execute("SELECT * FROM source_runs")',
    )
    value = value.replace(
        'history_rows = src.execute("SELECT * FROM proxy_history").fetchall()',
        'history_rows = src.execute("SELECT * FROM proxy_history")',
    )
    value = value.replace(
        '''                    existing = dst.execute(
                        "SELECT last_checked FROM source_stats WHERE url = ?",
                        (row["url"],),
                    ).fetchone()
                    if existing and int(existing[0]) >= int(row["last_checked"] or 0):
                        continue
''',
        '''                    existing = dst.execute(
                        "SELECT state_sequence, last_checked FROM source_stats WHERE url = ?",
                        (row["url"],),
                    ).fetchone()
                    source_sequence = (
                        int(row["state_sequence"] or 0)
                        if "state_sequence" in row.keys()
                        else 0
                    )
                    source_checked = int(row["last_checked"] or 0)
                    if existing:
                        destination_order = (int(existing[0] or 0), int(existing[1] or 0))
                        source_order = (source_sequence, source_checked)
                        if source_order <= destination_order:
                            continue
''',
    )
    value = value.replace(
        '''                            trust_score, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
''',
        '''                            trust_score, status, state_sequence
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''',
        1,
    )
    value = value.replace(
        '''                            trust_score=excluded.trust_score,
                            status=excluded.status
''',
        '''                            trust_score=excluded.trust_score,
                            status=excluded.status,
                            state_sequence=excluded.state_sequence
''',
        1,
    )
    value = value.replace(
        '''                            row["status"] if "status" in row.keys() else "active",
                        ),
''',
        '''                            row["status"] if "status" in row.keys() else "active",
                            source_sequence,
                        ),
''',
        1,
    )
    write(path, value)


def patch_small_reviews() -> None:
    replace(
        "src/configstream/config.py",
        "from typing import Optional",
        "from typing import Any, Optional",
    )
    replace(
        "src/configstream/config.py",
        "    def model_post_init(self, __context):",
        "    def model_post_init(self, __context: Any) -> None:",
    )
    replace(
        "src/configstream/config.py",
        '            "MAX_SEEN_KEYS",\n',
        '            "MAX_SEEN_KEYS",\n            "SEEN_BLOOM_EXPECTED_ITEMS",\n',
    )
    replace(
        "tests/unit/test_output.py",
        "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "3cc26273-917e-4268-a438-b181cf790d62",
        required=False,
    )
    replace(
        "docs/wiki/project/08-api-reference.md",
        "Xray is parser/Lab-only until a pipeline artifact is added",
        "Xray is released as xray.json with modern VMess/VLESS output, structural reference validation, and pinned native release checks",
        required=False,
    )
    replace(
        "scripts/validate_core_compatibility.py",
        '''            expected_core = (
                core if core in {"clash", "sing-box", "xray"} else core
            )
''',
        "            expected_core = core\n",
        required=False,
    )
    replace(
        "scripts/validate_pages_artifact.py",
        'XRAY_FILES = {"xray.json"}',
        '''XRAY_FILES = {
    path for path in REQUIRED_EXISTS if path.startswith("xray") and path.endswith(".json")
}''',
        required=False,
    )


def append_regressions() -> None:
    publication_tests = read("tests/unit/test_publication_policy.py")
    if "test_symlink_is_rejected" not in publication_tests:
        publication_tests += textwrap.dedent('''


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
        ''')
        write("tests/unit/test_publication_policy.py", publication_tests)

    quality_tests = read("tests/unit/quality/test_quality_components.py")
    if "test_record_run_without_explicit_key_is_idempotent" not in quality_tests:
        quality_tests += textwrap.dedent('''


            def test_record_run_without_explicit_key_is_idempotent(tmp_path):
                storage = QualityStorage(tmp_path / "quality.db")
                event = {
                    "timestamp": 123,
                    "duration_ms": 4.5,
                    "fetched_count": 2,
                    "working_count": 1,
                    "geoip_json": "{}",
                    "failure_modes_json": "{}",
                    "batch_source": "unit",
                }
                try:
                    assert storage.record_run("https://example.com/sub", event) is True
                    assert storage.record_run("https://example.com/sub", event) is False
                    count = storage.get_connection().execute(
                        "SELECT COUNT(*) FROM source_runs"
                    ).fetchone()[0]
                    assert count == 1
                finally:
                    storage.close()
        ''')
        write("tests/unit/quality/test_quality_components.py", quality_tests)


def main() -> int:
    patch_evidence()
    patch_output_contracts()
    patch_network_and_runtime()
    patch_storage_after_primary()
    patch_small_reviews()
    append_regressions()
    print("Applied expanded PR 531 review remediation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
