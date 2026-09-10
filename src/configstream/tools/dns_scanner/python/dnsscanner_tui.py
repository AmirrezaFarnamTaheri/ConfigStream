#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations
import logging
from typing import Any


import asyncio
import ipaddress
import mmap
import platform
import secrets
import stat
import subprocess  # nosec B404
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Set, AsyncGenerator, Optional, Deque, cast

import aiodns
import httpx
import orjson
from loguru import logger
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Static,
    RichLog,
    Input,
    Label,
    Checkbox,
    Select,
    DirectoryTree,
)

try:
    from .dnsscanner_lifecycle import (
        cancel_and_await_tasks as _cancel_and_await_tasks,
        kill_and_reap_processes as _kill_and_reap_processes,
    )
except ImportError:  # pragma: no cover - direct script execution compatibility
    from dnsscanner_lifecycle import (  # type: ignore[no-redef]
        cancel_and_await_tasks as _cancel_and_await_tasks,
        kill_and_reap_processes as _kill_and_reap_processes,
    )

try:
    from .slipstream_artifacts import (
        SLIPSTREAM_ARTIFACTS,
        download_verified_artifact,
        verify_artifact,
    )
except ImportError:  # pragma: no cover - direct script execution compatibility
    from slipstream_artifacts import (  # type: ignore[no-redef]
        SLIPSTREAM_ARTIFACTS,
        download_verified_artifact,
        verify_artifact,
    )

# Configure logging (disabled by default)
logger.remove()  # Remove default handler to disable all logging
# Uncomment below to enable file logging for debugging
# logger.add(
#     "logs/dnsscanner_{time}.log",
#     rotation="50 MB",
#     compression="zip",
#     level="DEBUG",
# )


class SlipstreamManager:
    """Manages slipstream client download and execution across platforms."""

    ARTIFACTS = SLIPSTREAM_ARTIFACTS

    FILENAMES = {key: value["filename"] for key, value in ARTIFACTS.items()}

    # Alternative names are accepted only when their contents match the pinned
    # digest for the active platform. Merely existing is never enough to execute.
    ALT_FILENAMES = {
        "Windows-x86_64": [
            "slipstream-client.exe",
            "slipstream-client-windows-amd64.exe",
        ],
        "Darwin-arm64": ["slipstream-client", "slipstream-client-darwin-arm64"],
        "Darwin-x86_64": ["slipstream-client", "slipstream-client-darwin-amd64"],
        "Linux-x86_64": ["slipstream-client", "slipstream-client-linux-amd64"],
        "Linux-arm64": ["slipstream-client", "slipstream-client-linux-arm64"],
    }

    PLATFORM_DIRS = {
        "Darwin": "macos",
        "Windows": "windows",
        "Linux": "linux",
    }

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent / "slipstream-client"
        self.system = platform.system()
        self.machine = platform.machine()
        self._cached_executable_path: Optional[Path] = None

        # Normalize machine architecture
        if self.machine in ("x86_64", "AMD64", "i386", "i686", "x86"):
            self.machine = "x86_64"
        elif self.machine == "aarch64":
            self.machine = "arm64"

    def is_supported(self) -> bool:
        """Return whether this platform has a pinned Slipstream artifact."""
        return f"{self.system}-{self.machine}" in self.ARTIFACTS

    def get_platform_key(self) -> str:
        """Return an architecture-specific key present in the pinned manifest."""
        key = f"{self.system}-{self.machine}"
        if key not in self.ARTIFACTS:
            raise RuntimeError(f"Unsupported platform: {self.system} {self.machine}")
        return key

    def _artifact(self) -> dict[str, str]:
        return self.ARTIFACTS[self.get_platform_key()]

    def get_platform_dir(self) -> Path:
        """Get the platform-specific directory."""
        dir_name = self.PLATFORM_DIRS.get(self.system, self.system.lower())
        return cast(Path, self.base_dir / dir_name)

    def get_executable_path(self) -> Path:
        """Return a verified installed path or the primary download destination."""
        artifact = self._artifact()
        expected_sha256 = artifact["sha256"]
        if self._cached_executable_path and verify_artifact(
            self._cached_executable_path, expected_sha256
        ):
            return self._cached_executable_path

        platform_key = self.get_platform_key()
        platform_dir = self.get_platform_dir()
        for filename in self.ALT_FILENAMES.get(platform_key, []):
            exe_path = platform_dir / filename
            if verify_artifact(exe_path, expected_sha256):
                self._cached_executable_path = exe_path
                return exe_path

        primary = self.FILENAMES.get(platform_key)
        if not primary:
            raise RuntimeError(f"Unsupported platform: {self.system} {self.machine}")
        return platform_dir / primary

    def is_installed(self) -> bool:
        """Return True only for a locally present binary matching the pinned digest."""
        artifact = self._artifact()
        expected_sha256 = artifact["sha256"]
        platform_key = self.get_platform_key()
        platform_dir = self.get_platform_dir()
        candidates = list(self.ALT_FILENAMES.get(platform_key, []))
        primary = self.FILENAMES.get(platform_key)
        if primary and primary not in candidates:
            candidates.append(primary)
        return any(
            verify_artifact(platform_dir / filename, expected_sha256)
            for filename in candidates
        )

    def get_download_url(self) -> Optional[str]:
        """Get the immutable release URL for the current platform."""
        try:
            return self._artifact()["url"]
        except RuntimeError:
            return None

    async def download(
        self, progress_callback=None, max_retries: int = 5, retry_delay: float = 2.0
    ) -> bool:
        """Download a pinned Slipstream binary and verify it before execution."""
        try:
            artifact = self._artifact()
        except RuntimeError:
            return False
        exe_path = self.get_platform_dir() / artifact["filename"]

        for attempt in range(1, max_retries + 1):
            ok = await download_verified_artifact(
                url=artifact["url"],
                expected_sha256=artifact["sha256"],
                destination=exe_path,
                progress_callback=progress_callback,
            )
            if ok:
                if self.system in ("Linux", "Darwin"):
                    exe_path.chmod(
                        exe_path.stat().st_mode
                        | stat.S_IXUSR
                        | stat.S_IXGRP
                        | stat.S_IXOTH
                    )
                self._cached_executable_path = exe_path
                return True
            if progress_callback:
                progress_callback(
                    0,
                    0,
                    f"Retry {attempt}/{max_retries}: verification or download failed",
                )
            if attempt < max_retries:
                await asyncio.sleep(retry_delay * attempt)
        return False

    async def download_with_ui(
        self, progress_bar, log_widget, max_retries: int = 5, retry_delay: float = 2.0
    ) -> bool:
        """Download with UI progress while retaining the same verification path."""
        last_logged_percent = -1

        def progress(downloaded: int, total: int, status: str) -> None:
            nonlocal last_logged_percent
            if total > 0:
                progress_bar.update_progress(downloaded, total)
                current_percent = int((downloaded / total) * 10) * 10
                if current_percent > last_logged_percent:
                    last_logged_percent = current_percent
                    log_widget.write(
                        f"[dim]Progress: {downloaded / (1024 * 1024):.1f}/"
                        f"{total / (1024 * 1024):.1f} MB ({current_percent}%)[/dim]"
                    )
            elif status:
                log_widget.write(f"[cyan]{status}[/cyan]")

        ok = await self.download(
            progress_callback=progress,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        if not ok:
            log_widget.write(
                "[red]Slipstream download failed or did not match the pinned SHA-256[/red]"
            )
        return ok

    def get_run_command(self, dns_ip: str, port: int, domain: str) -> list:
        """Get the command to run slipstream (same args for all platforms).

        Args:
            dns_ip: DNS server IP
            port: TCP listen port
            domain: Domain for slipstream

        Returns:
            List of command arguments
        """
        exe_path = str(self.get_executable_path())

        return [
            exe_path,
            "--resolver",
            f"{dns_ip}:53",
            "--resolver",
            "8.8.4.4:53",
            "--tcp-listen-port",
            str(port),
            "--domain",
            domain,
        ]


class StatsWidget(Static):
    """Display scan statistics."""

    found = reactive(0)
    scanned = reactive(0)
    total = reactive(0)
    speed = reactive(0.0)
    elapsed = reactive(0.0)

    def render(self) -> str:
        """Render the stats."""
        return f"""[b cyan]DNS Scanner Statistics[/b cyan]

[yellow]Total IPs:[/yellow] {self.total:,}
[yellow]Scanned:[/yellow] {self.scanned:,}
[green]Found:[/green] {self.found}
[yellow]Speed:[/yellow] {self.speed:.1f} IPs/sec
[yellow]Elapsed:[/yellow] {self.elapsed:.1f}s
"""


class CustomProgressBar(Static):
    """Custom progress bar with ▓▒ style and float percentage."""

    progress = reactive(0.0)
    total = reactive(100.0)
    bar_width = 40  # Width of the bar in characters

    def render(self) -> str:
        """Render the custom progress bar."""
        if self.total <= 0:
            percent = 0.0
        else:
            percent = (self.progress / self.total) * 100

        # Calculate filled portion
        filled = int((percent / 100) * self.bar_width)
        empty = self.bar_width - filled

        # Build the bar with ▓ for filled and ▒ for empty
        bar = "▓" * filled + "▒" * empty

        # Color: green for filled, dim for empty
        return f"[green]{bar[:filled]}[/green][dim]{bar[filled:]}[/dim] [cyan]{percent:.2f}%[/cyan]"

    def update_progress(self, progress: float, total: float) -> None:
        """Update progress values."""
        self.progress = progress
        self.total = total


class DNSScannerTUI(App):
    """DNS Scanner with Textual TUI."""

    ENABLE_COMMAND_PALETTE = False

    CSS = """
    Screen {
        background: $surface;
    }

    #start-screen {
        width: 100%;
        height: 100%;
        align: center middle;
    }

    #start-form {
        width: 80;
        height: auto;
        border: solid cyan;
        padding: 2;
        margin: 2;
    }

    #start-title {
        width: 100%;
        text-align: center;
        text-style: bold;
        color: cyan;
        padding: 1;
    }

    .form-row {
        width: 100%;
        height: 3;
        margin: 1 0;
    }

    .form-label {
        width: 20;
        padding: 0 1;
    }

    .form-input {
        width: 1fr;
    }

    #file-browser-container {
        width: 100%;
        height: 15;
        border: solid green;
        margin: 1 0;
        display: none;
    }

    DirectoryTree {
        height: 100%;
    }

    Select {
        width: 1fr;
    }

    #progress-container {
        width: 100%;
        height: 3;
        margin: 0 1;
        border: solid cyan;
        padding: 0 1;
    }

    #start-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 2;
    }

    #scan-screen {
        width: 100%;
        height: 100%;
    }

    #stats {
        width: 100%;
        height: auto;
        border: solid green;
        padding: 1;
        margin: 1;
    }

    #progress-bar {
        width: 100%;
        max-width: 100%;
        height: 1;
        content-align: center middle;
    }

    #main-content {
        width: 100%;
        height: 1fr;
    }

    #results {
        width: 60%;
        height: 100%;
        border: solid cyan;
        margin: 1;
    }

    #logs {
        width: 40%;
        height: 100%;
        border: solid yellow;
        margin: 1;
    }

    #controls {
        width: 100%;
        height: auto;
        margin: 1;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }

    DataTable {
        height: 100%;
    }

    RichLog {
        height: 100%;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "save_results", "Save"),
    ]

    def __init__(self):
        super().__init__()
        self.subnet_file = ""
        self.domain = ""
        self.dns_type = "A"
        self.concurrency = 100
        self.random_subdomain = False
        self.test_slipstream = False
        self.slipstream_manager = SlipstreamManager()
        # Resolve the platform-specific binary only if the user enables the
        # optional Slipstream path. Unsupported architectures can still use the
        # DNS scanner itself.
        self.slipstream_path = ""
        self.slipstream_domain = ""
        self.found_servers: Set[str] = set()
        self.server_times: dict[str, float] = {}
        self.proxy_results: dict[str, str] = {}
        self.start_time = 0.0
        self.last_update_time = 0.0
        self.last_table_update_time = 0.0
        self.current_scanned = 0
        self.table_needs_rebuild = False
        self.scan_started = False
        self.is_paused = False
        self.pause_event = asyncio.Event()
        self.pause_event.set()

        self.slipstream_max_concurrent = 3
        self.slipstream_base_port = 10800
        self.available_ports: Deque[int] = deque()
        self.slipstream_semaphore: asyncio.Semaphore = None
        self.pending_slipstream_tests: Deque[Any] = deque()
        self.slipstream_tasks: set = set()
        self.active_scan_tasks: list = []
        self._shutdown_event: asyncio.Event = None
        self.slipstream_processes: list = []

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header(show_clock=False)
        with Container(id="start-screen"):
            with Vertical(id="start-form"):
                yield Static("[b cyan]DNS Scanner Configuration[/b cyan]", id="start-title")
                with Horizontal(classes="form-row"):
                    yield Label("CIDR File:", classes="form-label")
                    yield Input(placeholder="Enter path or click Browse", id="input-file", classes="form-input")
                    yield Button("Browse", id="browse-btn", variant="primary")
                with Container(id="file-browser-container"):
                    yield DirectoryTree(".", id="file-browser")
                with Horizontal(classes="form-row"):
                    yield Label("Domain:", classes="form-label")
                    yield Input(placeholder="e.g., google.com", id="input-domain", classes="form-input", value="google.com")
                with Horizontal(classes="form-row"):
                    yield Label("DNS Type:", classes="form-label")
                    yield Select([("A (IPv4)", "A"), ("AAAA (IPv6)", "AAAA"), ("MX (Mail)", "MX"), ("TXT", "TXT"), ("NS", "NS")], value="A", id="input-type", classes="form-input")
                with Horizontal(classes="form-row"):
                    yield Label("Concurrency:", classes="form-label")
                    yield Input(placeholder="100", id="input-concurrency", classes="form-input", value="100")
                with Horizontal(classes="form-row"):
                    yield Label("Random Subdomain:", classes="form-label")
                    yield Checkbox("Enable", id="input-random")
                with Horizontal(classes="form-row"):
                    yield Label("Test with Slipstream:", classes="form-label")
                    yield Checkbox("Enable Proxy Test", id="input-slipstream")
                with Horizontal(id="start-buttons"):
                    yield Button("Start Scan", id="start-scan-btn", variant="success")
                    yield Button("Exit", id="exit-btn", variant="error")
        with Container(id="scan-screen"):
            yield StatsWidget(id="stats")
            with Container(id="progress-container"):
                yield CustomProgressBar(id="progress-bar")
            with Horizontal(id="main-content"):
                with Container(id="results"):
                    yield DataTable(id="results-table")
                with Container(id="logs"):
                    yield RichLog(id="log-display", highlight=True, markup=True)
            with Horizontal(id="controls"):
                yield Button("⏸  Pause", id="pause-btn", variant="warning")
                yield Button("▶  Resume", id="resume-btn", variant="primary")
                yield Button("Save Results", id="save-btn", variant="success")
                yield Button("Quit", id="quit-btn", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        self.theme = "dracula"
        self.query_one("#scan-screen").display = False
        table = self.query_one("#results-table", DataTable)
        table.add_columns("IP Address", "Response Time", "Status", "Proxy Test")
        table.cursor_type = "row"
        try:
            self.query_one("#pause-btn", Button).display = False
            self.query_one("#resume-btn", Button).display = False
        except Exception:  # nosec B110
            logging.getLogger(__name__).debug("Suppressed broad exception")

    async def action_quit(self) -> None:
        if self._shutdown_event is not None:
            self._shutdown_event.set()
        active_tasks = list(self.active_scan_tasks)
        slipstream_tasks = list(self.slipstream_tasks)
        processes = list(self.slipstream_processes)
        await _cancel_and_await_tasks(active_tasks + slipstream_tasks)
        await _kill_and_reap_processes(processes)
        self.active_scan_tasks.clear()
        self.slipstream_tasks.clear()
        self.slipstream_processes.clear()
        self.exit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-scan-btn":
            self._start_scan_from_form()
        elif event.button.id == "browse-btn":
            browser = self.query_one("#file-browser-container")
            browser.display = not browser.display
        elif event.button.id == "exit-btn":
            self.run_worker(self.action_quit())
        elif event.button.id == "pause-btn":
            self._pause_scan()
        elif event.button.id == "resume-btn":
            self._resume_scan()
        elif event.button.id == "save-btn":
            self.action_save_results()
        elif event.button.id == "quit-btn":
            self.run_worker(self.action_quit())

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        file_input = self.query_one("#input-file", Input)
        file_input.value = str(event.path)
        self.query_one("#file-browser-container").display = False

    def _pause_scan(self) -> None:
        if not self.scan_started or self.is_paused:
            return
        self.is_paused = True
        self.pause_event.clear()
        self._log("[yellow]⏸  Scan paused[/yellow]")
        self.notify("Scan paused", severity="warning")
        try:
            self.query_one("#pause-btn", Button).display = False
            self.query_one("#resume-btn", Button).display = True
        except Exception:  # nosec B110
            logging.getLogger(__name__).debug("Suppressed broad exception")

    def _resume_scan(self) -> None:
        if not self.scan_started or not self.is_paused:
            return
        self.is_paused = False
        self.pause_event.set()
        self._log("[green]▶  Scan resumed[/green]")
        self.notify("Scan resumed", severity="information")
        try:
            self.query_one("#pause-btn", Button).display = True
            self.query_one("#resume-btn", Button).display = False
        except Exception:  # nosec B110
            logging.getLogger(__name__).debug("Suppressed broad exception")

    def _start_scan_from_form(self) -> None:
        file_input = self.query_one("#input-file", Input)
        domain_input = self.query_one("#input-domain", Input)
        type_select = self.query_one("#input-type", Select)
        concurrency_input = self.query_one("#input-concurrency", Input)
        random_checkbox = self.query_one("#input-random", Checkbox)
        slipstream_checkbox = self.query_one("#input-slipstream", Checkbox)
        self.subnet_file = file_input.value.strip()
        self.domain = domain_input.value.strip()
        self.slipstream_domain = self.domain
        self.dns_type = str(type_select.value) if type_select.value else "A"
        self.random_subdomain = random_checkbox.value
        self.test_slipstream = slipstream_checkbox.value
        try:
            self.concurrency = int(concurrency_input.value.strip() or "100")
        except ValueError:
            self.concurrency = 100
        if not self.subnet_file:
            self.notify("Please enter a CIDR file path!", severity="error")
            return
        if not Path(self.subnet_file).exists():
            self.notify(f"File not found: {self.subnet_file}", severity="error")
            return
        if not self.domain:
            self.notify("Please enter a domain!", severity="error")
            return

        if self.test_slipstream and not self.slipstream_manager.is_supported():
            self.notify(
                f"Slipstream is unsupported on {self.slipstream_manager.system} {self.slipstream_manager.machine}",
                severity="error",
            )
            return
        if self.test_slipstream and self.slipstream_manager.is_installed():
            self.slipstream_path = str(self.slipstream_manager.get_executable_path())
        if self.test_slipstream and not self.slipstream_manager.is_installed():
            self.notify("Slipstream not found. Starting download...", severity="information")
            self.run_worker(self._download_and_start_scan(), exclusive=True)
            return

        self.query_one("#start-screen").display = False
        self.query_one("#scan-screen").display = True
        try:
            self.query_one("#pause-btn", Button).display = True
            self.query_one("#resume-btn", Button).display = False
        except Exception:  # nosec B110
            logging.getLogger(__name__).debug("Suppressed broad exception")
        log_widget = self.query_one("#log-display", RichLog)
        log_widget.write("[bold cyan]DNS Scanner Log[/bold cyan]")
        log_widget.write(f"[yellow]Subnet file:[/yellow] {self.subnet_file}")
        log_widget.write(f"[yellow]Domain:[/yellow] {self.domain}")
        log_widget.write(f"[yellow]DNS Type:[/yellow] {self.dns_type}")
        log_widget.write(f"[yellow]Concurrency:[/yellow] {self.concurrency}")
        log_widget.write(f"[yellow]Slipstream Test:[/yellow] {'Enabled' if self.test_slipstream else 'Disabled'}")
        log_widget.write("[green]Starting scan...[/green]\n")
        self.scan_started = True
        self.run_worker(self._scan_async(), exclusive=True)

    async def _download_and_start_scan(self) -> None:
        log_widget = self.query_one("#log-display", RichLog)
        progress_bar = self.query_one("#progress-bar", CustomProgressBar)
        self.query_one("#start-screen").display = False
        self.query_one("#scan-screen").display = True
        log_widget.write("[bold cyan]DNS Scanner Log[/bold cyan]")
        log_widget.write(f"[yellow]Platform:[/yellow] {self.slipstream_manager.system} {self.slipstream_manager.machine}")
        log_widget.write("[cyan]Downloading Slipstream client...[/cyan]")
        log_widget.write(f"[dim]URL: {self.slipstream_manager.get_download_url()}[/dim]")
        success = await self.slipstream_manager.download_with_ui(progress_bar=progress_bar, log_widget=log_widget)
        if success:
            log_widget.write("[green]✓ Slipstream downloaded successfully![/green]")
            progress_bar.update_progress(100, 100)
            self.slipstream_path = str(self.slipstream_manager.get_executable_path())
            log_widget.write(f"[yellow]Subnet file:[/yellow] {self.subnet_file}")
            log_widget.write(f"[yellow]Domain:[/yellow] {self.domain}")
            log_widget.write(f"[yellow]DNS Type:[/yellow] {self.dns_type}")
            log_widget.write(f"[yellow]Concurrency:[/yellow] {self.concurrency}")
            log_widget.write("[yellow]Slipstream Test:[/yellow] Enabled")
            log_widget.write("[green]Starting scan...[/green]\n")
            self.scan_started = True
            await self._scan_async()
        else:
            log_widget.write("[red]✗ Failed to download Slipstream after multiple retries![/red]")
            log_widget.write(f"[yellow]Expected path: {self.slipstream_manager.get_executable_path()}[/yellow]")
            log_widget.write("[yellow]Partial download saved. Run again to resume.[/yellow]")
            log_widget.write("[yellow]Or download manually and place in the path above.[/yellow]")
            self.notify("Failed to download Slipstream. Run again to resume.", severity="error")

    async def _scan_async(self) -> None:
        self.found_servers.clear()
        self.server_times.clear()
        self.proxy_results.clear()
        self.current_scanned = 0
        self.table_needs_rebuild = False
        self.is_paused = False
        self.pause_event = asyncio.Event()
        self.pause_event.set()
        self._shutdown_event = asyncio.Event()
        self.active_scan_tasks = []
        self.slipstream_semaphore = asyncio.Semaphore(self.slipstream_max_concurrent)
        self.available_ports = deque(range(self.slipstream_base_port, self.slipstream_base_port + self.slipstream_max_concurrent))
        self.pending_slipstream_tests.clear()
        self.slipstream_tasks.clear()
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.last_table_update_time = self.start_time
        self.notify("Reading CIDR file...", severity="information", timeout=3)
        self._log("[cyan]Analyzing CIDR file...[/cyan]")
        await asyncio.sleep(0)
        loop = asyncio.get_running_loop()
        line_count = await loop.run_in_executor(None, self._count_file_lines, self.subnet_file)
        if line_count == 0:
            self._log("[red]ERROR: No valid subnets found in file![/red]")
            self.notify("No valid subnets! Check CIDR file format.", severity="error")
            return
        self._log(f"[cyan]Found {line_count} CIDR entries. Starting scan...[/cyan]")
        await asyncio.sleep(0)
        estimated_ips = line_count * 254
        try:
            stats = self.query_one("#stats", StatsWidget)
            stats.total = estimated_ips
            progress_bar = self.query_one("#progress-bar", CustomProgressBar)
            progress_bar.update_progress(0, estimated_ips)
        except Exception:  # nosec B110
            logging.getLogger(__name__).debug("Suppressed broad exception")
        logger.info(f"Starting chunked scan with concurrency {self.concurrency}")
        self._log("[cyan]Scan mode: Streaming chunks (no pre-loading)[/cyan]")
        self._log(f"[cyan]Concurrency: {self.concurrency} workers[/cyan]")
        await asyncio.sleep(0)
        self.notify("Scanning in real-time...", severity="information", timeout=3)
        sem = asyncio.Semaphore(self.concurrency)
        self._log("[green]Starting real-time streaming scan...[/green]")
        await asyncio.sleep(0)
        chunk_size = 500
        active_tasks = []
        async for ip_chunk in self._stream_ips_from_file():
            if self._shutdown_event and self._shutdown_event.is_set():
                break
            await self.pause_event.wait()
            for ip in ip_chunk:
                task = asyncio.create_task(self._test_dns_with_callback(ip, sem))
                active_tasks.append(task)
            self.active_scan_tasks = active_tasks
            if len(active_tasks) >= chunk_size:
                await self.pause_event.wait()
                if self._shutdown_event and self._shutdown_event.is_set():
                    break
                done, pending_set = await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)
                active_tasks = list(pending_set)
                for task in done:
                    try:
                        result = await task
                        await self._process_result(result)
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logger.error(f"Task error: {e}")
                self.active_scan_tasks = active_tasks
                await asyncio.sleep(0)
        if self._shutdown_event and self._shutdown_event.is_set():
            self._log("[yellow]Scan interrupted - cleaning up...[/yellow]")
            await _cancel_and_await_tasks(active_tasks)
            self.active_scan_tasks.clear()
            return
        self._log("[cyan]Finishing remaining scans...[/cyan]")
        if active_tasks:
            done, _ = await asyncio.wait(active_tasks)
            for task in done:
                try:
                    result = await task
                    await self._process_result(result)
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Task error: {e}")
        self._log(f"[cyan]Scan complete. Scanned: {self.current_scanned}, Found: {len(self.found_servers)}[/cyan]")
        logger.info(f"Scan complete. Scanned: {self.current_scanned}, Found: {len(self.found_servers)}")
        try:
            stats = self.query_one("#stats", StatsWidget)
            stats.scanned = self.current_scanned
            stats.found = len(self.found_servers)
            elapsed = time.time() - self.start_time
            stats.elapsed = elapsed
            stats.speed = self.current_scanned / elapsed if elapsed > 0 else 0
            stats.total = self.current_scanned
            progress_bar = self.query_one("#progress-bar", CustomProgressBar)
            progress_bar.update_progress(self.current_scanned, self.current_scanned)
        except Exception:  # nosec B110
            logging.getLogger(__name__).debug("Suppressed broad exception")
        self._rebuild_table()
        if self.test_slipstream and self.slipstream_tasks:
            num_tasks = len(self.slipstream_tasks)
            self._log(f"[cyan]Waiting for {num_tasks} slipstream tests to complete (max 60s)...[/cyan]")
            try:
                await asyncio.wait_for(asyncio.gather(*self.slipstream_tasks, return_exceptions=True), timeout=60.0)
            except asyncio.TimeoutError:
                self._log("[yellow]Timeout waiting for slipstream tests - cancelling remaining tests[/yellow]")
                await _cancel_and_await_tasks(self.slipstream_tasks)
            self._rebuild_table()
        self._auto_save_results()
        self.notify("Scan complete! Results auto-saved.", severity="information")

    def _count_file_lines(self, filepath: str) -> int:
        count = 0
        try:
            with open(filepath, "rb") as f:
                for line in f:
                    line_str = line.strip()
                    if line_str and not line_str.startswith(b"#"):
                        count += 1
        except Exception:  # nosec B110
            logging.getLogger(__name__).debug("Suppressed broad exception")
        return count

    def _load_subnets(self) -> list[ipaddress.IPv4Network]:
        subnets = []
        logger.info(f"Loading subnets from {self.subnet_file}")
        try:
            with open(self.subnet_file, "r+b") as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped:
                    for line in iter(mmapped.readline, b""):
                        try:
                            line_str = line.decode("utf-8", errors="ignore").strip()
                            if line_str and not line_str.startswith("#"):
                                subnets.append(ipaddress.IPv4Network(line_str, strict=False))
                        except Exception as e:
                            logger.warning(f"Failed to parse line: {line_str[:50]} - {e}")
        except (ValueError, OSError) as e:
            logger.warning(f"mmap failed: {e}, falling back to regular reading")
            try:
                with open(self.subnet_file, "r", encoding="utf-8") as f:
                    for line_txt in f:
                        line_clean = line_txt.strip()
                        if line_clean and not line_clean.startswith("#"):
                            try:
                                subnets.append(ipaddress.IPv4Network(line_clean, strict=False))
                            except Exception as e:
                                logger.warning(f"Failed to parse line: {line_clean[:50]} - {e}")
            except Exception as e:
                logger.error(f"Failed to read subnet file: {e}")
        logger.info(f"Loaded {len(subnets)} subnets")
        return subnets

    async def _stream_ips_from_file(self) -> AsyncGenerator[list[str], None]:
        chunk = []
        chunk_size = 500
        rng = secrets.SystemRandom()
        loop = asyncio.get_running_loop()

        def read_and_process():
            subnets = []
            try:
                with open(self.subnet_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            try:
                                subnet = ipaddress.IPv4Network(line, strict=False)
                                subnets.append(subnet)
                            except Exception:  # nosec B110
                                logging.getLogger(__name__).debug("Suppressed broad exception")
            except Exception as e:
                logger.error(f"Failed to read file: {e}")
            return subnets

        subnets = await loop.run_in_executor(None, read_and_process)
        rng.shuffle(subnets)
        for net in subnets:
            chunks = [net] if net.prefixlen >= 24 else list(net.subnets(new_prefix=24))
            rng.shuffle(chunks)
            for subnet_chunk in chunks:
                if subnet_chunk.num_addresses == 1:
                    chunk.append(str(subnet_chunk.network_address))
                else:
                    ips = list(subnet_chunk.hosts())
                    rng.shuffle(ips)
                    for ip in ips:
                        chunk.append(str(ip))
                        if len(chunk) >= chunk_size:
                            yield chunk
                            chunk = []
                            await asyncio.sleep(0)
        if chunk:
            yield chunk

    async def _test_dns_with_callback(self, ip: str, sem: asyncio.Semaphore) -> tuple[str, bool, float]:
        await self.pause_event.wait()
        return await self._test_dns(ip, sem)

    async def _process_result(self, result: tuple[str, bool, float]) -> None:
        if isinstance(result, tuple):
            ip, is_valid, response_time = result
            self.current_scanned += 1
            if is_valid:
                self._add_result(ip, response_time)
                self._log(f"[green]✓ Found DNS: {ip} ({response_time * 1000:.0f}ms)[/green]")
                if self.test_slipstream:
                    self.proxy_results[ip] = "Pending"
                    task = asyncio.create_task(self._queue_slipstream_test(ip))
                    self.slipstream_tasks.add(task)
                    task.add_done_callback(self.slipstream_tasks.discard)
            if self.current_scanned % 10 == 0:
                current_time = time.time()
                elapsed = current_time - self.start_time
                try:
                    stats = self.query_one("#stats", StatsWidget)
                    stats.scanned = self.current_scanned
                    stats.elapsed = elapsed
                    stats.speed = self.current_scanned / elapsed if elapsed > 0 else 0
                    stats.found = len(self.found_servers)
                    progress_bar = self.query_one("#progress-bar", CustomProgressBar)
                    progress_bar.update_progress(self.current_scanned, stats.total)
                except Exception:  # nosec B110
                    logging.getLogger(__name__).debug("Suppressed broad exception")

    def _collect_ips(self, subnets: list[ipaddress.IPv4Network]) -> list[str]:
        all_ips = []
        rng = secrets.SystemRandom()
        subnets_copy = list(subnets)
        rng.shuffle(subnets_copy)
        for net in subnets_copy:
            chunks = [net] if net.prefixlen >= 24 else list(net.subnets(new_prefix=24))
            rng.shuffle(chunks)
            for chunk in chunks:
                if chunk.num_addresses == 1:
                    all_ips.append(str(chunk.network_address))
                else:
                    ips = list(chunk.hosts())
                    rng.shuffle(ips)
                    all_ips.extend([str(ip) for ip in ips])
        return all_ips

    async def _test_dns(self, ip: str, sem: asyncio.Semaphore) -> tuple[str, bool, float]:
        async with sem:
            try:
                domain = self.domain
                if self.random_subdomain:
                    prefix = secrets.token_hex(4)
                    domain = f"{prefix}.{domain}"
                resolver = aiodns.DNSResolver(nameservers=[ip], timeout=2.0, tries=1)
                start = time.time()
                try:
                    result = await resolver.query(domain, self.dns_type)
                    elapsed = time.time() - start
                    if result and elapsed < 2.0:
                        return (ip, True, elapsed)
                    if result:
                        return (ip, False, 0)
                    return (ip, False, 0)
                except aiodns.error.DNSError as dns_err:
                    elapsed = time.time() - start
                    error_code = dns_err.args[0] if dns_err.args else 0
                    if error_code in (1, 3, 4) and elapsed < 2.0:
                        return (ip, True, elapsed)
                    return (ip, False, 0)
            except asyncio.TimeoutError:
                return (ip, False, 0)
            except Exception:
                logging.getLogger(__name__).debug("Suppressed broad exception")
                return (ip, False, 0)

    def _add_result(self, ip: str, response_time: float) -> None:
        self.found_servers.add(ip)
        self.server_times[ip] = response_time
        try:
            table = self.query_one("#results-table", DataTable)
            server_ms = response_time * 1000
            if server_ms < 100:
                server_time_str = f"[green]{server_ms:.0f}ms[/green]"
            elif server_ms < 300:
                server_time_str = f"[yellow]{server_ms:.0f}ms[/yellow]"
            else:
                server_time_str = f"[red]{server_ms:.0f}ms[/red]"
            proxy_status = self.proxy_results.get(ip, "N/A")
            if proxy_status == "Success":
                proxy_str = "[green]✓ Passed[/green]"
            elif proxy_status == "Failed":
                proxy_str = "[red]✗ Failed[/red]"
            elif proxy_status == "Testing":
                proxy_str = "[yellow]Testing...[/yellow]"
            elif proxy_status == "Pending":
                proxy_str = "[dim]Queued[/dim]"
            else:
                proxy_str = "[dim]N/A[/dim]"
            table.add_row(ip, server_time_str, "[green]Active[/green]", proxy_str)
        except Exception:  # nosec B110
            logging.getLogger(__name__).debug("Suppressed broad exception")
        self.table_needs_rebuild = True
        current_time = time.time()
        if current_time - self.last_table_update_time >= 2.0:
            self._rebuild_table()
            self.last_table_update_time = current_time

    def _rebuild_table(self) -> None:
        if not self.table_needs_rebuild:
            return
        try:
            table = self.query_one("#results-table", DataTable)
            table.clear()
            sorted_servers = sorted(self.server_times.items(), key=lambda x: x[1])
            for server_ip, server_time in sorted_servers:
                server_ms = server_time * 1000
                server_time_str = f"[green]{server_ms:.0f}ms[/green]" if server_ms < 100 else (f"[yellow]{server_ms:.0f}ms[/yellow]" if server_ms < 300 else f"[red]{server_ms:.0f}ms[/red]")
                proxy_status = self.proxy_results.get(server_ip, "N/A")
                proxy_str = {"Success": "[green]✓ Passed[/green]", "Failed": "[red]✗ Failed[/red]", "Testing": "[yellow]Testing...[/yellow]", "Pending": "[dim]Queued[/dim]"}.get(proxy_status, "[dim]N/A[/dim]")
                table.add_row(server_ip, server_time_str, "[green]Active[/green]", proxy_str)
            self.table_needs_rebuild = False
        except Exception:  # nosec B110
            logging.getLogger(__name__).debug("Suppressed broad exception")

    async def _queue_slipstream_test(self, dns_ip: str) -> None:
        async with self.slipstream_semaphore:
            while not self.available_ports:
                await asyncio.sleep(0.1)
            port = self.available_ports.popleft()
            try:
                self.proxy_results[dns_ip] = "Testing"
                self._update_table_row(dns_ip)
                self._log(f"[cyan]Testing {dns_ip} with slipstream on port {port}...[/cyan]")
                result = await self._test_slipstream_proxy(dns_ip, port)
                self.proxy_results[dns_ip] = result
                self._log(f"[green]✓ Proxy test PASSED: {dns_ip}[/green]" if result == "Success" else f"[red]✗ Proxy test FAILED: {dns_ip}[/red]")
                self._update_table_row(dns_ip)
            finally:
                self.available_ports.append(port)

    def _update_table_row(self, ip: str) -> None:
        self.table_needs_rebuild = True
        self._rebuild_table()

    async def _test_slipstream_proxy(self, dns_ip: str, port: int) -> str:
        process = None
        try:
            cmd = self.slipstream_manager.get_run_command(dns_ip, port, self.slipstream_domain)
            process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, creationflags=(getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0))
            self.slipstream_processes.append(process)
            connection_ready = False
            try:
                async def wait_for_connection_ready():
                    nonlocal connection_ready
                    while True:
                        line = await process.stdout.readline()
                        if not line:
                            break
                        line_str = line.decode("utf-8", errors="ignore").strip()
                        if "Connection ready" in line_str:
                            connection_ready = True
                            return
                await asyncio.wait_for(wait_for_connection_ready(), timeout=15)
            except asyncio.TimeoutError:
                return "Failed"
            if not connection_ready:
                return "Failed"
            await asyncio.sleep(1.5)
            proxy_url = f"http://127.0.0.1:{port}"
            test_success = False
            try:
                async with httpx.AsyncClient(proxy=proxy_url, timeout=15.0, follow_redirects=True) as client:
                    response = await client.get("http://google.com")
                    if response.status_code in (200, 301, 302):
                        test_success = True
            except Exception:
                try:
                    async with httpx.AsyncClient(proxy=f"socks5://127.0.0.1:{port}", timeout=15.0, follow_redirects=True) as client:
                        response = await client.get("http://google.com")
                        if response.status_code in (200, 301, 302):
                            test_success = True
                except Exception:
                    pass
            return "Success" if test_success else "Failed"
        except Exception as e:
            logger.error(f"[{dns_ip}] Slipstream error: {type(e).__name__}: {str(e)}", exc_info=True)
            self._log(f"[red]Slipstream error for {dns_ip}: {str(e)[:50]}[/red]")
            return "Failed"
        finally:
            if process:
                try:
                    process.kill()
                    await process.wait()
                    if process in self.slipstream_processes:
                        self.slipstream_processes.remove(process)
                except Exception:  # nosec B110
                    logging.getLogger(__name__).debug("Suppressed broad exception")

    def _log(self, message: str) -> None:  # type: ignore[override]
        try:
            log_widget = self.query_one("#log-display", RichLog)
            log_widget.write(message)
        except Exception:  # nosec B110
            logging.getLogger(__name__).debug("Suppressed broad exception")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = self.query_one("#results-table", DataTable)
        row = table.get_row(event.row_key)
        if row and len(row) > 0:
            ip = str(row[0]).strip()
            try:
                import pyperclip
                pyperclip.copy(ip)
                self.notify(f"{ip} copied!", severity="information", timeout=2)
            except Exception as e:
                self.notify(f"Copy failed: {str(e)[:30]}", severity="warning")

    def _auto_save_results(self) -> None:
        if self.test_slipstream:
            passed_servers = {ip: t for ip, t in self.server_times.items() if self.proxy_results.get(ip) == "Success"}
            if not passed_servers:
                self._log("[yellow]No DNS servers passed proxy test - nothing to save.[/yellow]")
                return
            servers_to_save = passed_servers
        else:
            if not self.found_servers:
                self._log("[yellow]No DNS servers found to save.[/yellow]")
                return
            servers_to_save = self.server_times
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = Path("results")
        output_dir.mkdir(exist_ok=True)
        txt_file = output_dir / f"{timestamp}.txt"
        sorted_servers = sorted(servers_to_save.items(), key=lambda x: x[1])
        with open(txt_file, "w") as f:
            f.write(f"# DNS Scanner Results - {timestamp}\n")
            f.write(f"# Domain: {self.domain} | Type: {self.dns_type}\n")
            if self.test_slipstream:
                f.write("# Slipstream Test: ENABLED (only passed servers)\n")
            f.write(f"# Total Saved: {len(servers_to_save)}\n")
            f.write("#" + "=" * 50 + "\n\n")
            for server_ip, _server_time in sorted_servers:
                f.write(f"{server_ip}\n")
        self._log(f"[green]✓ Results auto-saved to: {txt_file}[/green]")

    def action_save_results(self) -> None:
        if self.test_slipstream:
            passed_servers = {ip: t for ip, t in self.server_times.items() if self.proxy_results.get(ip) == "Success"}
            if not passed_servers:
                self.notify("No servers passed proxy test!", severity="warning")
                return
            servers_to_save = passed_servers
        else:
            if not self.found_servers:
                self.notify("No results to save!", severity="warning")
                return
            servers_to_save = self.server_times
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = Path("results")
        output_dir.mkdir(exist_ok=True)
        json_file = output_dir / f"scan_{timestamp}.json"
        elapsed = time.time() - self.start_time
        sorted_servers = sorted(servers_to_save.items(), key=lambda x: x[1])
        servers_list = [ip for ip, _ in sorted_servers]
        data = {"scan_info": {"domain": self.domain, "dns_type": self.dns_type, "slipstream_test": self.test_slipstream, "total_found": len(self.found_servers), "total_passed_proxy": (len([ip for ip in self.proxy_results if self.proxy_results[ip] == "Success"]) if self.test_slipstream else 0), "total_saved": len(servers_to_save), "elapsed_seconds": elapsed, "timestamp": timestamp}, "servers": servers_list}
        with open(json_file, "wb") as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
        txt_file = output_dir / f"scan_{timestamp}.txt"
        with open(txt_file, "w") as f:
            for server in servers_list:
                f.write(f"{server}\n")
        self.notify(f"Saved {len(servers_list)} servers: {json_file.name}", severity="information")


def main():
    try:
        Path("logs").mkdir(exist_ok=True)
        Path("results").mkdir(exist_ok=True)
        app = DNSScannerTUI()
        app.run()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
