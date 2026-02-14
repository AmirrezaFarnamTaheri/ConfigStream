# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Fuzz Testing for Parsers.
Uses Hypothesis to generate random, malformed inputs to ensure robustness.
"""

from hypothesis import given, strategies as st, settings, HealthCheck
from configstream.auto_detect import auto_detect_and_parse as parse_config
from configstream.parsers import extract_config_lines

# Strategy: Generate text that contains potential URI characters but is random
# We mix printable characters, control characters, and unicode to stress the parser
fuzz_strategy = st.text(
    alphabet=st.characters(blacklist_categories=["Cs"]),  # Avoid surrogates
    min_size=0,
    max_size=1000,
)


@settings(
    max_examples=1000, suppress_health_check=[HealthCheck.too_slow], deadline=None
)
@given(fuzz_strategy)
def test_parser_does_not_crash(config_str):
    """
    Property: parse_config should NEVER raise an unhandled exception.
    It should either return a Proxy object or None.
    """
    try:
        parse_config(config_str)
    except Exception as e:
        # These are the ONLY acceptable exceptions (if any).
        # Ideally, parse_config catches everything and returns None.
        # If this block is reached, we found a bug.
        raise AssertionError(f"Parser crashed on input: {config_str!r} with error: {e}")


@settings(max_examples=500)
@given(st.text())
def test_extractor_resilience(raw_content):
    """
    Property: extract_config_lines should handle arbitrary text blobs without crashing.
    """
    try:
        lines, stats = extract_config_lines(raw_content)
        assert isinstance(lines, list)
        assert isinstance(stats, dict)
    except Exception as e:
        raise AssertionError(
            f"Extractor crashed on input: {raw_content!r} with error: {e}"
        )
