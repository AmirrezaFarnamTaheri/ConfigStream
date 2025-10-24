#!/usr/bin/env python3
"""
CHANGELOG.md validation script

This script ensures that your CHANGELOG follows best practices and doesn't
contain any future dates that would confuse users about release history.

Why this matters:
-----------------
A CHANGELOG is your project's historical record. Having future dates in it
suggests either carelessness or that the file hasn't been properly maintained.
It breaks tools that parse changelog dates and confuses users trying to
understand when features were actually released.

This script runs in CI to catch these issues before they reach production.

Usage:
------
    # Run locally:
    python scripts/validate_changelog.py

    # In GitHub Actions:
    - name: Validate CHANGELOG
      run: python scripts/validate_changelog.py

Exit codes:
-----------
0: All checks passed
1: Validation errors found
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def extract_dates_from_changelog(content: str) -> list[tuple[str, str]]:
    """
    Extract version and date pairs from CHANGELOG.md

    Looks for lines matching the pattern:
    ## [0.4.0] - 2025-01-15

    Args:
        content: CHANGELOG.md file content

    Returns:
        List of (version, date_string) tuples

    Example:
        content = "## [0.4.0] - 2025-01-15\\n## [0.3.0] - 2025-01-10"
        result = extract_dates_from_changelog(content)
        # Returns: [('0.4.0', '2025-01-15'), ('0.3.0', '2025-01-10')]
    """
    # Regex pattern explanation:
    # ##\s*         - Two hashes followed by optional whitespace
    # \[([^\]]+)\]  - Capture version inside square brackets
    # \s*-\s*       - Optional whitespace around dash
    # (\d{4}-\d{2}-\d{2})  - Capture date in YYYY-MM-DD format
    pattern = r"##\s*\[([^\]]+)\]\s*-\s*(\d{4}-\d{2}-\d{2})"

    matches = re.findall(pattern, content)
    return matches


def validate_date(date_string: str) -> tuple[bool, str]:
    """
    Check if date is not in the future

    We use UTC for consistency, since your GitHub Actions runs on UTC.

    Args:
        date_string: Date string in YYYY-MM-DD format

    Returns:
        Tuple of (is_valid, error_message)
        error_message is empty string if valid

    Example:
        # Past date - valid
        is_valid, error = validate_date('2024-01-15')
        assert is_valid is True

        # Future date - invalid
        is_valid, error = validate_date('2099-12-31')
        assert is_valid is False
        assert 'future' in error.lower()
    """
    try:
        # Parse the date
        date = datetime.strptime(date_string, "%Y-%m-%d")
        date = date.replace(tzinfo=timezone.utc)

        # Get current date in UTC
        now = datetime.now(timezone.utc)

        # Check if date is in future
        # We compare just the date portion to avoid issues with time-of-day
        if date.date() > now.date():
            return False, f"Date {date_string} is in the future"

        return True, ""

    except ValueError as exc:
        return False, f"Invalid date format: {exc}"


def validate_version_ordering(entries: list[tuple[str, str]]) -> list[str]:
    """
    Check that versions appear in reverse chronological order

    Your CHANGELOG should have newest versions at the top and oldest at
    the bottom. This function checks that dates are in descending order.

    Args:
        entries: List of (version, date) tuples from changelog

    Returns:
        List of error messages (empty if all valid)

    Example:
        # Correct ordering (newest first)
        entries = [('0.4.0', '2025-01-15'), ('0.3.0', '2025-01-10')]
        errors = validate_version_ordering(entries)
        assert len(errors) == 0

        # Wrong ordering
        entries = [('0.3.0', '2025-01-10'), ('0.4.0', '2025-01-15')]
        errors = validate_version_ordering(entries)
        assert len(errors) > 0
    """
    errors = []

    # Convert dates to datetime objects for comparison
    dated_entries = []
    for version, date_str in entries:
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
            dated_entries.append((version, date))
        except ValueError:
            # Invalid date format - caught by validate_date
            continue

    # Check each pair of adjacent entries
    for i in range(len(dated_entries) - 1):
        current_version, current_date = dated_entries[i]
        next_version, next_date = dated_entries[i + 1]

        # Current (higher in file) should have later or equal date
        if current_date < next_date:
            errors.append(
                f"Version {current_version} ({current_date}) appears "
                f"before {next_version} ({next_date}), but has an earlier date. "
                f"Versions should be in reverse chronological order."
            )

    return errors


def main():
    """Main validation function"""
    # Locate CHANGELOG.md
    # This works whether script is run from project root or scripts directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    changelog_path = project_root / "CHANGELOG.md"

    # Check file exists
    if not changelog_path.exists():
        print("❌ ERROR: CHANGELOG.md not found")
        print(f"   Expected location: {changelog_path}")
        return 1

    # Read content
    content = changelog_path.read_text(encoding="utf-8")

    # Extract dated entries
    entries = extract_dates_from_changelog(content)

    if not entries:
        print("⚠️  WARNING: No dated changelog entries found")
        print("   Expected format: ## [0.4.0] - 2025-01-15")
        return 0  # Not an error, just a warning

    print(f"📋 Found {len(entries)} dated entries in CHANGELOG")

    # Validate each date
    errors = []

    for version, date_string in entries:
        is_valid, error_msg = validate_date(date_string)
        if not is_valid:
            errors.append(f"Version {version}: {error_msg}")

    # Validate ordering
    ordering_errors = validate_version_ordering(entries)
    errors.extend(ordering_errors)

    # Report results
    if errors:
        print("\\n❌ CHANGELOG VALIDATION FAILED:")
        for error in errors:
            print(f"   - {error}")
        return 1

    print("✅ All CHANGELOG validations passed")
    print(f"   Validated {len(entries)} version entries")
    print(f"   Date range: {entries[-1][1]} to {entries[0][1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
