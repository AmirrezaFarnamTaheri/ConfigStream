# SPDX-License-Identifier: AGPL-3.0-or-later
"""Static verification test for WASM panic recovery in go source."""
from pathlib import Path

def test_wasm_main_contains_defer_recover():
    wasm_main = Path("src/go/tester/wasm_main.go")
    assert wasm_main.exists()
    content = wasm_main.read_text(encoding="utf-8")
    assert "recover()" in content
