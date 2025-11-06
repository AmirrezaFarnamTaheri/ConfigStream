#!/usr/bin/env python3
"""
Script to fix lazy logging throughout the codebase.
Converts f-string logging to % formatting for better performance.

Usage:
    python scripts/fix_lazy_logging.py --dry-run  # Preview changes
    python scripts/fix_lazy_logging.py            # Apply changes
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple
import argparse


def find_python_files(directory: Path) -> List[Path]:
    """Find all Python files in directory."""
    return list(directory.rglob("*.py"))


def extract_fstring_variables(fstring: str) -> List[str]:
    """Extract variable names from f-string."""
    # Match {variable} or {expression}
    pattern = r"\{([^}]+)\}"
    matches = re.findall(pattern, fstring)
    return matches


def convert_fstring_to_percent(fstring: str) -> Tuple[str, List[str]]:
    """
    Convert f-string to % formatting.

    Returns:
        Tuple of (format_string, [variables])
    """
    variables = []

    def replacer(match):
        var = match.group(1)
        # Check if this is a simple variable or complex expression
        # Skip complex expressions with brackets/slicing
        if "[" in var or "(" in var:
            # For complex expressions, just keep them as-is
            variables.append(var)
            return "%s"

        variables.append(var)
        # Handle format specs like {x:.2f}
        if ":" in var:
            var_name, format_spec = var.split(":", 1)
            variables[-1] = var_name  # Store just the variable name
            return f"%{format_spec}"
        return "%s"

    # Replace {var} with %s
    pattern = r"\{([^}]+)\}"
    format_string = re.sub(pattern, replacer, fstring)

    return format_string, variables


def fix_logging_line(line: str) -> str | None:
    """
    Fix a logging line if it uses f-strings.

    Returns:
        Fixed line or None if no changes needed
    """
    # Match logger.{level}(f"...") or logger.{level}(f'...')
    pattern = r'(logger\.(debug|info|warning|error|critical|exception))\(f(["\'])(.+?)\3\)'

    match = re.search(pattern, line)
    if not match:
        return None

    logger_call = match.group(1)
    quote_char = match.group(3)
    fstring_content = match.group(4)

    # Convert f-string to % format
    format_string, variables = convert_fstring_to_percent(fstring_content)

    # Build new logging call
    if variables:
        vars_str = ", ".join(variables)
        new_call = f"{logger_call}({quote_char}{format_string}{quote_char}, {vars_str})"
    else:
        # No variables, just remove f prefix
        new_call = f"{logger_call}({quote_char}{format_string}{quote_char})"

    # Replace in original line
    new_line = line[: match.start()] + new_call + line[match.end() :]

    return new_line


def process_file(file_path: Path, dry_run: bool = True) -> int:
    """
    Process a single file and fix lazy logging.

    Returns:
        Number of lines changed
    """
    try:
        content = file_path.read_text()
        lines = content.splitlines(keepends=True)

        changes = 0
        new_lines = []

        for line_num, line in enumerate(lines, start=1):
            fixed_line = fix_logging_line(line)

            if fixed_line and fixed_line != line:
                changes += 1
                if dry_run:
                    print(f"\n{file_path}:{line_num}")
                    print(f"  - {line.strip()}")
                    print(f"  + {fixed_line.strip()}")
                new_lines.append(fixed_line)
            else:
                new_lines.append(line)

        # Write back if not dry run and changes were made
        if not dry_run and changes > 0:
            file_path.write_text("".join(new_lines))
            print(f"✓ Fixed {changes} lines in {file_path}")

        return changes

    except Exception as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)
        return 0


def main():
    parser = argparse.ArgumentParser(description="Fix lazy logging in Python files")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without applying them"
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("src/configstream"),
        help="Path to search for Python files",
    )

    args = parser.parse_args()

    source_dir = args.path
    if not source_dir.exists():
        print(f"Error: {source_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Scanning {source_dir}...")

    python_files = find_python_files(source_dir)
    print(f"Found {len(python_files)} Python files")

    total_changes = 0
    files_changed = 0

    for file_path in python_files:
        changes = process_file(file_path, dry_run=args.dry_run)
        if changes > 0:
            total_changes += changes
            files_changed += 1

    print(
        f"\n{'Would fix' if args.dry_run else 'Fixed'} {total_changes} lines in {files_changed} files"
    )

    if args.dry_run and total_changes > 0:
        print("\nRun without --dry-run to apply changes")


if __name__ == "__main__":
    main()
