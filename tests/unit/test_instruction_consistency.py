# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path

from scripts.validate_instruction_consistency import validate


def test_contributor_instructions_match_current_repository() -> None:
    assert validate(Path('.')) == []
