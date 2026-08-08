# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import re
import sys
from pathlib import Path

ENCODING = "utf-8"


def main() -> None:
    root = Path(".")

    pyproject = (root / "pyproject.toml").read_text(encoding=ENCODING)
    version_match = re.search(r'version = "(.*?)"', pyproject)
    if not version_match:
        print("ERROR: Could not find version in pyproject.toml")
        sys.exit(1)
    truth_version = version_match.group(1)
    print(f"Target Version: {truth_version}")

    errors: list[str] = []

    changelog = (root / "CHANGELOG.md").read_text(encoding=ENCODING)
    if f"[{truth_version}]" not in changelog:
        errors.append(f"CHANGELOG.md missing entry for [{truth_version}]")

    js_config = (root / "frontend/assets/js/cache-config.js").read_text(
        encoding=ENCODING
    )
    if f"VERSION: 'v{truth_version}'" not in js_config:
        errors.append(
            f"frontend/assets/js/cache-config.js version mismatch. "
            f"Expected 'v{truth_version}'"
        )

    readiness = json.loads((root / "docs/readiness.json").read_text(encoding=ENCODING))
    if readiness.get("project_version") != truth_version:
        errors.append("docs/readiness.json project_version mismatch")

    dockerfile = (root / "Dockerfile").read_text(encoding=ENCODING)
    if f'org.opencontainers.image.version="{truth_version}"' not in dockerfile:
        errors.append("Dockerfile OCI image version mismatch")

    revival = (root / "src/configstream_revival/__init__.py").read_text(
        encoding=ENCODING
    )
    if f'__version__ = "{truth_version}"' not in revival:
        errors.append("configstream_revival version mismatch")

    if errors:
        print("ERROR: Version Validation Failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print("OK: All versions synchronized.")


if __name__ == "__main__":
    main()
