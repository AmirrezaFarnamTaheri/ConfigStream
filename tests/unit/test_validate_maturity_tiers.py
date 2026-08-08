# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path
from scripts.validate_maturity_tiers import validate


def test_repository_maturity_tiers_are_explicit_and_valid() -> None:
    assert validate(Path(".")) == []
