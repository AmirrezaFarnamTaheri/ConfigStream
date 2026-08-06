# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path

from scripts.validate_function_size_budget import scan, validate


def test_function_size_budget_is_exact() -> None:
    assert validate(Path('.')) == []


def test_function_size_scan_covers_known_hotspots() -> None:
    functions = scan(Path('.'))
    assert 'src/configstream/converters/singbox.py::to_singbox_outbound' in functions
    assert 'src/configstream/pipeline/producer.py::source_producer' in functions
