# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path

from scripts import dynamic_reshard
from configstream.security_validator import SecurityValidator


def test_raw_timing_does_not_fan_out_across_sanitizer_collision(tmp_path: Path) -> None:
    """Ambiguous sanitized observations must remain pessimistically unobserved."""

    first = "https://example.com/sub?token=first"
    second = "https://example.com/sub?token=second"
    sanitized = SecurityValidator.sanitize_log_message(first)
    assert sanitized == SecurityValidator.sanitize_log_message(second)

    log = tmp_path / "pipeline_batch_1_part_1.log"
    log.write_text(
        f"Source Summary [{sanitized}]: Raw=100 Fetch=50ms Dur=2500ms\n",
        encoding="utf-8",
    )

    metrics = dynamic_reshard.parse_logs(
        [str(log)],
        test_time_per_proxy=0.03,
        allowed_urls={first, second},
        normalized_map={dynamic_reshard._normalize_source_key(first): [first, second]},
    )

    assert metrics == {}


def test_raw_timing_can_resolve_one_unique_sanitized_source(tmp_path: Path) -> None:
    """A single candidate remains usable when structured evidence is unavailable."""

    source = "https://example.com/sub?token=only"
    sanitized = SecurityValidator.sanitize_log_message(source)
    log = tmp_path / "pipeline_batch_1_part_1.log"
    log.write_text(
        f"Source Summary [{sanitized}]: Raw=100 Fetch=50ms Dur=2500ms\n",
        encoding="utf-8",
    )

    metrics = dynamic_reshard.parse_logs(
        [str(log)],
        test_time_per_proxy=0.03,
        allowed_urls={source},
        normalized_map={dynamic_reshard._normalize_source_key(source): [source]},
    )

    assert metrics == {source: (100, 2.5)}
