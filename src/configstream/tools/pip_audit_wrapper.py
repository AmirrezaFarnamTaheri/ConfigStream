"""Project-specific pip-audit wrapper utilities."""

from __future__ import annotations

import subprocess
import sys


def main() -> None:
    """Invoke pip-audit for the current project by default."""

    passthrough_args = sys.argv[1:]
    has_positional = any(not arg.startswith("-") for arg in passthrough_args)
    extra_args: list[str] = []
    if not has_positional:
        extra_args.append(".")

    completed = subprocess.run(
        [sys.executable, "-m", "pip_audit", *passthrough_args, *extra_args],
        check=False,
    )
    raise SystemExit(completed.returncode)


if __name__ == "__main__":  # pragma: no cover - passthrough entry point
    main()
