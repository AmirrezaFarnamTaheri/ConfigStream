# SPDX-License-Identifier: AGPL-3.0-or-later
"""Remove only Bandit suppression tokens that no longer hide an active finding."""

from __future__ import annotations

from pathlib import Path

from scripts.validate_bandit_suppressions import (
    SCAN_ROOTS,
    _bandit_findings,
    _iter_python_files,
    _NOSEC_RE,
    _repo_relative,
    _RULE_RE,
)


def main() -> None:
    findings = _bandit_findings()
    changed_files = 0
    removed_tokens = 0

    for path in _iter_python_files():
        relative = _repo_relative(path)
        original = path.read_text(encoding="utf-8")
        lines = original.splitlines(keepends=True)
        changed = False

        for index, line in enumerate(lines, start=1):
            match = _NOSEC_RE.search(line)
            if not match:
                continue
            tokens = [token.upper() for token in _RULE_RE.findall(match.group(1) or "")]
            if not tokens:
                continue
            active = findings.get((relative, index), set())
            retained = [token for token in tokens if token in active]
            removed_tokens += len(tokens) - len(retained)
            if retained == tokens:
                continue

            replacement = "# nosec " + ", ".join(retained) if retained else ""
            new_line = line[: match.start()] + replacement + line[match.end() :]
            if not replacement:
                new_line = new_line.rstrip(" \t\r\n") + ("\n" if line.endswith("\n") else "")
            lines[index - 1] = new_line
            changed = True

        if changed:
            path.write_text("".join(lines), encoding="utf-8")
            changed_files += 1

    print(
        f"Removed {removed_tokens} stale Bandit suppression token(s) "
        f"from {changed_files} file(s) across {', '.join(str(root) for root in SCAN_ROOTS)}"
    )


if __name__ == "__main__":
    main()
