# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path
from scripts.validate_release_controls import validate


def test_required_release_controls_are_preserved() -> None:
    assert validate(Path(".")) == []
