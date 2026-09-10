# SPDX-License-Identifier: AGPL-3.0-or-later
import ast
import asyncio
from pathlib import Path

import pytest

from configstream.tools.dns_scanner.python.dnsscanner_lifecycle import (
    cancel_and_await_tasks as _cancel_and_await_tasks,
    kill_and_reap_processes as _kill_and_reap_processes,
)


@pytest.mark.asyncio
async def test_cancel_and_await_tasks_runs_task_finalizers() -> None:
    finalized = asyncio.Event()

    async def worker() -> None:
        try:
            await asyncio.Event().wait()
        finally:
            finalized.set()

    task = asyncio.create_task(worker())
    await asyncio.sleep(0)

    await _cancel_and_await_tasks([task])

    assert task.done()
    assert finalized.is_set()


@pytest.mark.asyncio
async def test_kill_and_reap_processes_waits_for_children() -> None:
    class Process:
        returncode = None

        def __init__(self) -> None:
            self.killed = False
            self.waited = 0

        def kill(self) -> None:
            self.killed = True
            self.returncode = -9

        async def wait(self) -> int | None:
            self.waited += 1
            return self.returncode

    process = Process()

    await _kill_and_reap_processes([process], timeout=0.1)

    assert process.killed is True
    assert process.waited == 1


@pytest.mark.asyncio
async def test_kill_and_reap_processes_reaps_already_exited_child() -> None:
    class Process:
        returncode = 0

        def __init__(self) -> None:
            self.killed = False
            self.waited = 0

        def kill(self) -> None:
            self.killed = True

        async def wait(self) -> int | None:
            self.waited += 1
            return self.returncode

    process = Process()

    await _kill_and_reap_processes([process], timeout=0.1)

    assert process.killed is False
    assert process.waited == 1


def _tui_source_tree() -> ast.Module:
    source = Path(
        "src/configstream/tools/dns_scanner/python/dnsscanner_tui.py"
    ).read_text(encoding="utf-8")
    return ast.parse(source)


def test_tui_initialization_defers_unsupported_slipstream() -> None:
    """Lock the lazy-init contract without importing optional TUI dependencies."""
    tree = _tui_source_tree()

    tui_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "DNSScannerTUI"
    )
    init = next(
        node
        for node in tui_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "__init__"
    )

    eager_resolution = [
        node
        for node in ast.walk(init)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get_executable_path"
    ]
    assert eager_resolution == []

    assert any(
        isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
            and target.attr == "slipstream_path"
            for target in node.targets
        )
        and isinstance(node.value, ast.Constant)
        and node.value.value == ""
        for node in ast.walk(init)
    )

    start_scan = next(
        node
        for node in tui_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "_start_scan_from_form"
    )
    called_attributes = {
        node.func.attr
        for node in ast.walk(start_scan)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "is_supported" in called_attributes
    assert "get_executable_path" in called_attributes


def test_tui_does_not_require_undeclared_loguru_dependency() -> None:
    """The scanner TUI must import using only dependencies declared by the project."""
    tree = _tui_source_tree()

    imported_modules = {
        alias.name.split(".", 1)[0]
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_modules.update(
        node.module.split(".", 1)[0]
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module
    )

    assert "loguru" not in imported_modules
    assert any(
        isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr == "getLogger"
        for node in tree.body
    )
