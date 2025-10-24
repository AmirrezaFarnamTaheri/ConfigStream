"""Tests for adaptive worker scaling."""

from configstream.adaptive_workers import calculate_optimal_workers


def test_calculate_optimal_workers_basic():
    """Test basic worker calculation."""
    workers = calculate_optimal_workers()

    # Should return a reasonable number
    assert 8 <= workers <= 32


def test_calculate_optimal_workers_with_limits():
    """Test worker calculation respects limits."""
    workers = calculate_optimal_workers(max_workers=16, min_workers=4)

    assert 4 <= workers <= 16


def test_calculate_optimal_workers_never_zero():
    """Test that worker count is never zero."""
    workers = calculate_optimal_workers(min_workers=1)

    assert workers >= 1
