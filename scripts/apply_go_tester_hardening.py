# SPDX-License-Identifier: AGPL-3.0-or-later
"""Apply the reviewed base-manager Go tester hardening transformation once."""

from __future__ import annotations

import ast
from pathlib import Path

TARGET = Path("src/configstream/testers/go_tester/manager.py")


def replace_once(source: str, old: str, new: str, description: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one {description} block, found {count}")
    return source.replace(old, new, 1)


def main() -> None:
    source = TARGET.read_text(encoding="utf-8")

    source = replace_once(source, "import tempfile\n", "", "tempfile import")
    source = replace_once(
        source,
        "from .interfaces import BatchTester\n",
        "from .binary_security import (\n"
        "    BinaryIdentity,\n"
        "    initialize_binary_identity,\n"
        "    minimal_subprocess_environment,\n"
        "    verify_binary_identity,\n"
        ")\n"
        "from .interfaces import BatchTester\n",
        "go tester local imports",
    )
    source = replace_once(
        source,
        "        self.binary_path = resolved or binary_path\n"
        "        self.available = resolved is not None\n",
        "        self.binary_path = resolved or binary_path\n"
        "        self.available = resolved is not None\n"
        "        self._binary_identity: Optional[BinaryIdentity] = None\n"
        "        if self.available:\n"
        "            try:\n"
        "                self._binary_identity = initialize_binary_identity(\n"
        "                    self.binary_path\n"
        "                )\n"
        "                self.binary_path = str(self._binary_identity.path)\n"
        "            except (OSError, ValueError) as exc:\n"
        "                logger.error(\n"
        "                    \"Go tester binary rejected: %s\", str(exc)\n"
        "                )\n"
        "                self.available = False\n",
        "binary availability initialization",
    )
    source = replace_once(
        source,
        "            settings = AppSettings()\n"
        "            cmd = [\n",
        "            settings = AppSettings()\n"
        "            if self._binary_identity is None:\n"
        "                self.available = False\n"
        "                return\n"
        "            try:\n"
        "                await asyncio.to_thread(\n"
        "                    verify_binary_identity, self._binary_identity\n"
        "                )\n"
        "            except (OSError, ValueError) as exc:\n"
        "                logger.error(\n"
        "                    \"Go tester integrity verification failed: %s\",\n"
        "                    str(exc),\n"
        "                )\n"
        "                self.available = False\n"
        "                return\n"
        "            cmd = [\n",
        "pre-spawn integrity check",
    )
    source = replace_once(
        source,
        "            env = os.environ.copy()\n"
        "            env[\"GOLOG_LOG_LEVEL\"] = \"error\"\n"
        "            env[\"TMPDIR\"] = os.environ.get(\"TMPDIR\", tempfile.gettempdir())\n"
        "            if not env.get(\"PATH\"):\n"
        "                env[\"PATH\"] = os.defpath\n",
        "            env = minimal_subprocess_environment(settings)\n",
        "subprocess environment construction",
    )

    ast.parse(source, filename=str(TARGET))
    TARGET.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()
