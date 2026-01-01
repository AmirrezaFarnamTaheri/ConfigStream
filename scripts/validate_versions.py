# SPDX-License-Identifier: AGPL-3.0-or-later
import sys
import re
from pathlib import Path


def main():
    root = Path(".")

    # 1. Get Source of Truth (pyproject.toml)
    pyproject = (root / "pyproject.toml").read_text()
    version_match = re.search(r'version = "(.*?)"', pyproject)
    if not version_match:
        print("❌ Could not find version in pyproject.toml")
        sys.exit(1)
    truth_version = version_match.group(1)
    print(f"🔹 Target Version: {truth_version}")

    errors = []

    # 2. Check Changelog
    changelog = (root / "CHANGELOG.md").read_text()
    if f"[{truth_version}]" not in changelog:
        errors.append(f"CHANGELOG.md missing entry for [{truth_version}]")

    # 3. Check Frontend Config
    js_config = (root / "frontend/assets/js/cache_config.js").read_text()
    if f"VERSION: 'v{truth_version}'" not in js_config:
        errors.append(
            f"frontend/assets/js/cache_config.js version mismatch. Expected 'v{truth_version}'"
        )

    # 4. Check Init
    # init_py = (root / "src/configstream/__init__.py").read_text()
    # Note: init uses importlib, so we check if the fallback matches or if it's dynamic
    # Ideally, we don't hardcode version in init.py, so this check is soft.

    if errors:
        print("❌ Version Validation Failed:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("✅ All versions synchronized.")


if __name__ == "__main__":
    main()
