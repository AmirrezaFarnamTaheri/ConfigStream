# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from scripts.generate_debt_matrix import _is_false_positive


def test_parameterized_sql_in_clause_is_not_reported_as_placeholder_debt() -> None:
    assert _is_false_positive(
        "PLACEHOLDER", "WHERE proxy_id IN ({placeholders})"
    )


def test_real_placeholder_sentinel_remains_actionable() -> None:
    assert not _is_false_positive(
        "PLACEHOLDER", 'raise RuntimeError("PLACEHOLDER_NOT_CONFIGURED")'
    )
