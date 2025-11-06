#!/usr/bin/env python3
"""
Script to fix lazy logging throughout the codebase.
Converts f-string logging to % formatting for better performance.

Uses AST-based transformation for safe and robust code transformation.

Usage:
    python scripts/fix_lazy_logging.py --dry-run  # Preview changes
    python scripts/fix_lazy_logging.py            # Apply changes
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import List


class LoggingFStringTransformer(ast.NodeTransformer):
    """Transform logger calls with f-strings to use % formatting."""

    LOG_METHODS = {"debug", "info", "warning", "error", "critical", "exception"}

    def __init__(self):
        self.changes = 0

    def visit_Call(self, node: ast.Call) -> ast.AST:
        """Visit call nodes and transform logger f-string calls."""
        self.generic_visit(node)

        # Match logger.<level>(f"...", *args, **kwargs)
        if not isinstance(node.func, ast.Attribute):
            return node
        if not isinstance(node.func.value, ast.Name):
            return node
        if node.func.value.id != "logger":
            return node
        if node.func.attr not in self.LOG_METHODS:
            return node
        if not node.args:
            return node
        if not isinstance(node.args[0], ast.JoinedStr):
            return node

        # Convert f-string to % format
        try:
            fmt_str, var_nodes = self._convert_joinedstr(node.args[0])

            # Build new args: format string literal + variables
            new_args: list[ast.expr] = [ast.Constant(value=fmt_str, kind=None)]
            new_args.extend(var_nodes)

            # Preserve remaining args and kwargs
            new_args.extend(node.args[1:])

            node.args = new_args
            self.changes += 1
        except Exception:
            # If conversion fails, leave node unchanged
            pass

        return node

    def _convert_joinedstr(self, joined: ast.JoinedStr) -> tuple[str, list[ast.expr]]:
        """
        Convert JoinedStr (f-string) to format string and variables.

        Returns:
            Tuple of (format_string, [variable_nodes])
        """
        fmt_parts: list[str] = []
        var_nodes: list[ast.expr] = []

        for value in joined.values:
            if isinstance(value, ast.FormattedValue):
                # Handle format spec if present
                if value.format_spec and isinstance(value.format_spec, ast.JoinedStr):
                    # Extract format spec from the JoinedStr
                    spec_parts = []
                    for spec_value in value.format_spec.values:
                        if isinstance(spec_value, ast.Constant):
                            spec_parts.append(str(spec_value.value))
                    format_spec = "".join(spec_parts)
                    fmt_parts.append(f"%{format_spec}")
                else:
                    fmt_parts.append("%s")
                var_nodes.append(value.value)
            elif isinstance(value, ast.Constant) and isinstance(value.value, str):
                # Literal string part
                fmt_parts.append(value.value)

        return "".join(fmt_parts), var_nodes


def process_file(file_path: Path, dry_run: bool = True) -> int:
    """
    Process a single file and fix lazy logging.

    Returns:
        Number of changes made
    """
    try:
        source = file_path.read_text()
        tree = ast.parse(source)

        # Transform the AST
        transformer = LoggingFStringTransformer()
        new_tree = transformer.visit(tree)

        if transformer.changes == 0:
            return 0

        # Generate new source code
        ast.fix_missing_locations(new_tree)
        new_source = ast.unparse(new_tree)

        if dry_run:
            print(f"\n{file_path}: {transformer.changes} change(s) detected")
            return int(transformer.changes)

        # Write back the modified source
        file_path.write_text(new_source)
        print(f"✓ Fixed {transformer.changes} logging call(s) in {file_path}")
        return int(transformer.changes)

    except SyntaxError as e:
        print(f"Syntax error in {file_path}:{e.lineno}: {e.msg}", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)
        return 0


def find_python_files(directory: Path) -> List[Path]:
    """Find all Python files in directory."""
    return list(directory.rglob("*.py"))


def main():
    parser = argparse.ArgumentParser(
        description="Fix lazy logging in Python files using AST transformation"
    )
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
        f"\n{'Would fix' if args.dry_run else 'Fixed'} {total_changes} logging call(s) in {files_changed} file(s)"
    )

    if args.dry_run and total_changes > 0:
        print("\nRun without --dry-run to apply changes")


if __name__ == "__main__":
    main()
