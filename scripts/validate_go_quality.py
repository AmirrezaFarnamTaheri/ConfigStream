# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate that native Go modules have unit, race, fuzz, and benchmark gates."""
from __future__ import annotations
from pathlib import Path


def validate(root: Path) -> list[str]:
    root = Path(root)
    errors: list[str] = []
    required_files = (
        'src/go/tester/main_test.go',
        'src/go/tester/scanner/scanner_test.go',
        'src/go/utls_client/main_test.go',
    )
    for relative in required_files:
        if not (root / relative).is_file():
            errors.append(f'missing native test file: {relative}')
    combined = '\n'.join((root / path).read_text(encoding='utf-8') for path in required_files if (root / path).is_file())
    for token in ('FuzzParseConfig', 'FuzzParseTarget', 'BenchmarkParseConfig', 'BenchmarkParseTarget'):
        if token not in combined:
            errors.append(f'missing Go fuzz/benchmark target: {token}')
    workflow = (root / '.github/workflows/ci.yml').read_text(encoding='utf-8')
    for command in (
        'go test ./...',
        'go test -race ./...',
        '-fuzz=FuzzParseConfig',
        '-fuzz=FuzzParseTarget',
        '-bench=.',
    ):
        if command not in workflow:
            errors.append(f'CI missing Go quality command: {command}')
    return errors


def main() -> int:
    errors = validate(Path('.'))
    if errors:
        print('ERROR: Go quality validation failed')
        for error in errors: print(f'  - {error}')
        return 1
    print('OK: Go unit, race, fuzz, and benchmark gates are declared')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
