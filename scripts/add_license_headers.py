#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Adds SPDX license headers to source files.
"""

from pathlib import Path

SPDX_HEADER = """# SPDX-License-Identifier: AGPL-3.0-or-later
"""

GO_HEADER = """// SPDX-License-Identifier: AGPL-3.0-or-later
"""


def add_header(path: Path, header: str):
    try:
        content = path.read_text(encoding="utf-8")
        if "SPDX-License-Identifier" in content:
            return

        # Preserve shebang if present
        if content.startswith("#!"):
            lines = content.splitlines(keepends=True)
            if len(lines) > 0:
                lines.insert(1, header)
                new_content = "".join(lines)
            else:
                new_content = content + header
        else:
            new_content = header + content

        path.write_text(new_content, encoding="utf-8")
        print(f"Added header to {path}")
    except Exception as e:
        print(f"Failed to process {path}: {e}")


def main():
    root = Path(".")

    # Process Python
    for path in root.rglob("*.py"):
        if "venv" in str(path) or ".git" in str(path):
            continue
        add_header(path, SPDX_HEADER)

    # Process Go
    for path in root.rglob("*.go"):
        if "vendor" in str(path):
            continue
        add_header(path, GO_HEADER)


if __name__ == "__main__":
    main()
