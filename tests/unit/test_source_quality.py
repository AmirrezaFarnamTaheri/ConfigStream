# SPDX-License-Identifier: AGPL-3.0-or-later
from configstream.source_quality import SourceQualityTracker


def test_source_quality_scoring(tmp_path):
    db_path = tmp_path / "quality.db"
    tracker = SourceQualityTracker(db_path=db_path)  # Pass Path object

    source = "http://example.com/list"
    tracker.update(source, fetched=100, working=80, diversity=0.5)

    # Should fetch
    should = tracker.should_fetch(source)
    assert should is True


def test_source_quality_decay(tmp_path):
    db_path = tmp_path / "quality.db"
    tracker = SourceQualityTracker(db_path=db_path)  # Pass Path object
    source = "http://example.com/bad"

    # Consistent failure
    for _ in range(5):
        tracker.update(source, fetched=100, working=0, diversity=0.0)

    # It should ideally set cooldown, but logic depends on timestamps.
    # Exponential backoff sets cooldown in hours.
    # Testing exact score requires inspecting DB or exposing get_score.
    # SourceQualityTracker has get_source_score logic.
    # Wait, get_source_score wasn't in the version I read in memory but might be in file?
    # I see get_source_score in the file content I just read.

    score = tracker.get_source_score(source)
    assert score < 50.0
