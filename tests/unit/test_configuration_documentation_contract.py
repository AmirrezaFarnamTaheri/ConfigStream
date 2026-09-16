# SPDX-License-Identifier: AGPL-3.0-or-later

from pathlib import Path
import re

from configstream.config import AppSettings


REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DOC = REPO_ROOT / "docs/wiki/project/Configuration.md"
ENV_EXAMPLE = REPO_ROOT / ".env.example"


def _documented_defaults() -> dict[str, str]:
    values: dict[str, str] = {}
    row = re.compile(r"^\| `(?P<name>[A-Z0-9_]+)` \| `(?P<default>[^`]*)` \|")
    for line in CONFIG_DOC.read_text(encoding="utf-8").splitlines():
        match = row.match(line)
        if match:
            values[match.group("name")] = match.group("default")
    return values


def _render_default(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value if value else '""'
    return str(value)


def test_authoritative_configuration_doc_matches_runtime_defaults() -> None:
    documented = _documented_defaults()
    governed_fields = (
        "TEST_TIMEOUT",
        "BATCH_TIME_LIMIT_SECONDS",
        "BATCH_TIME_LIMIT_GRACE_SECONDS",
        "GO_TESTER_BATCH_SIZE",
        "GO_TESTER_MAX_CONSECUTIVE_TIMEOUTS",
        "PY_TESTER_BATCH_SIZE",
        "MAX_REMOTE_TEST_CANDIDATES_PER_SOURCE",
        "STRICT_SECURITY",
        "UPDATE_INTERVAL_HOURS",
    )

    for name in governed_fields:
        assert name in documented, f"missing documented default for {name}"
        default = AppSettings.model_fields[name].default
        assert documented[name] == _render_default(default), (
            f"{name} docs={documented[name]!r} runtime={default!r}"
        )


def test_removed_source_url_limit_is_not_advertised_as_live_configuration() -> None:
    assert "MAX_SOURCE_URL_LENGTH" not in AppSettings.model_fields
    assert "MAX_SOURCE_URL_LENGTH" not in CONFIG_DOC.read_text(encoding="utf-8")
    assert "MAX_SOURCE_URL_LENGTH" not in ENV_EXAMPLE.read_text(encoding="utf-8")
