# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Command Line Interface for ConfigStream.
"""

import asyncio
import logging
import sys
import os
import shutil
import tarfile
from pathlib import Path

import click
import requests  # type: ignore
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

from .geoip import DEFAULT_RESOLVER
from .tools.warp import generate_warp_proxy
from .pipeline import run_full_pipeline
from .logging_config import SensitiveDataFilter
from .config import AppSettings

# Initialize Rich Console
console = Console()


def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    settings = AppSettings()
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)],
    )
    if settings.MASK_SENSITIVE_DATA:
        for handler in logging.getLogger().handlers:
            handler.addFilter(SensitiveDataFilter())
    # Silence noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


@click.group()
@click.version_option()
def main():
    """ConfigStream: Automated Proxy Aggregator & Tester"""
    try:
        import uvloop  # type: ignore

        # Prevent uvloop installation during tests to avoid conflicts with pytest-asyncio
        if "pytest" not in sys.modules and "PYTEST_CURRENT_TEST" not in os.environ:
            uvloop.install()
    except ImportError:
        pass


@main.command()
@click.option("--sources", multiple=True, help="Path to source files")
@click.option("--output", default="output", help="Output directory")
@click.option("--verbose", is_flag=True, help="Enable debug logging")
def merge(sources, output, verbose):
    """Run the aggregation and testing pipeline."""
    setup_logging(verbose)
    console.print(f"[bold blue]Starting ConfigStream Pipeline...[/bold blue]")

    try:
        # Use Rich Progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Processing...", total=None)
            
            # This is a synchronous wrapper around the async pipeline
            # In a real scenario, we might want to integrate progress updates into the pipeline callbacks
            result = asyncio.run(run_full_pipeline(list(sources), output))
            
            progress.update(task, completed=100)

        if result.success:
            stats = result.stats
            # Helper to safely get values from stats object or dict
            def _get(k):
                if hasattr(stats, k):
                    return getattr(stats, k)
                return stats.get(k, 0)

            console.print("\n[bold green]Pipeline Completed Successfully![/bold green]")
            console.print(f"Duration: {_get('duration'):.1f}s")
            console.print(f"Fetched: {_get('fetched_lines')}")
            console.print(f"Tested: {_get('tested')}")
            console.print(f"Working: {_get('working')}")
            console.print(f"GeoIP: {_get('geo_resolved')}")
            
            time_limited = False
            if hasattr(stats, "time_limited"):
                time_limited = bool(stats.time_limited)
            elif isinstance(stats, dict):
                time_limited = bool(stats.get("time_limited", False))
            if time_limited:
                console.print(
                    "[yellow]Time limit reached; output contains partial results.[/yellow]"
                )
        else:
            console.print(f"\n[bold red]Pipeline Failed: {result.error}[/bold red]")
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Pipeline interrupted by user.[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[bold red]Fatal Error: {e}[/bold red]")
        if verbose:
            console.print_exception()
        sys.exit(1)
    finally:
        # Cleanup singleton resources
        DEFAULT_RESOLVER.close()


@main.command()
def update_databases():
    """Download latest GeoIP databases."""
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)

    console.print("[yellow]Downloading GeoIP databases...[/yellow]")

    from .config import AppSettings
    from .security_validator import SecurityValidator

    license_key = AppSettings().MAXMIND_LICENSE_KEY

    # Prefer official MaxMind downloads when a license key is provided, fall back to public mirror otherwise.
    mirror_base_urls = [
        "https://github.com/FyraLabs/geolite2/releases/latest/download",
        "https://github.com/P3TERX/GeoLite.mmdb/raw/download",
    ]

    maxmind_editions = {
        "GeoLite2-City.mmdb": "GeoLite2-City",
        "GeoLite2-ASN.mmdb": "GeoLite2-ASN",
    }
    
    # Geosite and GeoIP databases for Sing-box routing rules
    singbox_databases = {
        "geosite.db": "https://github.com/SagerNet/sing-geosite/releases/latest/download/geosite.db",
        "geoip.db": "https://github.com/SagerNet/sing-geoip/releases/latest/download/geoip.db",
    }

    def stream_download(url: str, target: Path) -> bool:
        safe_url = SecurityValidator.sanitize_log_message(url)
        try:
            with requests.get(url, stream=True, timeout=120) as resp:
                if resp.status_code != 200:
                    console.print(
                        f"[red]HTTP {resp.status_code} while fetching {safe_url}[/red]"
                    )
                    return False
                with target.open("wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            return target.exists() and target.stat().st_size > 0
        except requests.RequestException as exc:
            safe_exc = SecurityValidator.sanitize_log_message(str(exc))
            console.print(f"[red]Request error for {safe_url}: {safe_exc}[/red]")
            return False
        except Exception as exc:  # pragma: no cover - best effort logging
            safe_exc = SecurityValidator.sanitize_log_message(str(exc))
            console.print(f"[red]Unexpected error for {safe_url}: {safe_exc}[/red]")
            return False

    def download_from_maxmind(edition: str, target: Path) -> bool:
        if not license_key:
            return False

        tar_path = target.with_suffix(".tar.gz")
        url = (
            "https://download.maxmind.com/app/geoip_download"
            f"?edition_id={edition}&license_key={license_key}&suffix=tar.gz"
        )
        console.print(f"[cyan]Fetching {edition} from MaxMind...[/cyan]")

        if not stream_download(url, tar_path):
            return False

        try:
            with tarfile.open(tar_path, "r:gz") as archive:
                member = next(
                    (
                        m
                        for m in archive.getmembers()
                        if m.name.endswith(f"{edition}.mmdb")
                    ),
                    None,
                )
                if not member:
                    console.print(f"[red]{edition}.mmdb not found in archive[/red]")
                    return False
                extracted = archive.extractfile(member)
                if extracted is None:
                    console.print(f"[red]Archive entry for {edition} is empty[/red]")
                    return False
                with target.open("wb") as dest:
                    shutil.copyfileobj(extracted, dest)
            return target.exists() and target.stat().st_size > 0
        except Exception as exc:
            console.print(f"[red]Failed to extract {edition}: {exc}[/red]")
            return False
        finally:
            if tar_path.exists():
                tar_path.unlink(missing_ok=True)

    success = True
    for name, edition in maxmind_editions.items():
        target = data_dir / name

        if target.exists() and target.stat().st_size > 0:
            size_mb = target.stat().st_size / (1024 * 1024)
            console.print(f"[green]OK {name} already exists ({size_mb:.1f} MB)[/green]")
            continue

        downloaded = download_from_maxmind(edition, target)

        if not downloaded:
            for base_url in mirror_base_urls:
                mirror_url = f"{base_url}/{name}"
                console.print(f"[cyan]Trying mirror {base_url} for {name}...[/cyan]")
                if stream_download(mirror_url, target):
                    downloaded = True
                    break

        if downloaded and target.stat().st_size > 0:
            size_mb = target.stat().st_size / (1024 * 1024)
            console.print(f"[green]OK {name} ({size_mb:.1f} MB)[/green]")
        else:
            console.print(f"[red]Failed to download {name}[/red]")
            success = False

    # Download Sing-box databases (geosite.db and geoip.db) for routing rules
    console.print("[yellow]Downloading Sing-box databases (geosite.db, geoip.db)...[/yellow]")
    singbox_data_dir = data_dir / "singbox"
    singbox_data_dir.mkdir(parents=True, exist_ok=True)
    
    singbox_databases = {
        "geosite.db": "https://github.com/SagerNet/sing-geosite/releases/latest/download/geosite.db",
        "geoip.db": "https://github.com/SagerNet/sing-geoip/releases/latest/download/geoip.db",
    }
    
    singbox_success = True
    for db_name, db_url in singbox_databases.items():
        target = singbox_data_dir / db_name
        
        if target.exists() and target.stat().st_size > 0:
            size_mb = target.stat().st_size / (1024 * 1024)
            console.print(f"[green]OK {db_name} already exists ({size_mb:.1f} MB)[/green]")
            continue
        
        console.print(f"[cyan]Downloading {db_name}...[/cyan]")
        if stream_download(db_url, target):
            if target.stat().st_size > 0:
                size_mb = target.stat().st_size / (1024 * 1024)
                console.print(f"[green]OK {db_name} ({size_mb:.1f} MB)[/green]")
            else:
                console.print(f"[red]Failed to download {db_name} (empty file)[/red]")
                singbox_success = False
        else:
            console.print(f"[red]Failed to download {db_name}[/red]")
            singbox_success = False
    
    if success and singbox_success:
        console.print("[bold green]All databases updated successfully[/bold green]")
        sys.exit(0)
    elif success:
        console.print("[yellow]GeoIP databases updated, but Sing-box databases failed[/yellow]")
        sys.exit(0)  # Non-fatal for Sing-box DBs
    else:
        console.print("[bold red]Failed to download one or more databases[/bold red]")
        sys.exit(1)


@main.command()
@click.option("--count", default=1, help="Number of configs to generate")
def generate_warp(count):
    """Generate Cloudflare WARP configuration templates."""
    console.print(f"[yellow]Generating {count} WARP config template(s)...[/yellow]")

    import asyncio

    async def _gen():
        for i in range(count):
            p = await generate_warp_proxy()
            console.print(f"\n[bold green]Config #{i+1}:[/bold green]")
            console.print(f"Protocol: {p.protocol}")
            console.print(f"Details: {p.details}")
            console.print(f"[dim]{p.config}[/dim]")

    coro = _gen()
    try:
        asyncio.run(coro)
    except RuntimeError as e:
        coro.close()
        if "no current event loop" in str(e).lower():
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                loop.run_until_complete(_gen())
            finally:
                loop.close()
                asyncio.set_event_loop(None)
        else:
            raise

    console.print(
        "\n[dim]Note: Real key generation requires the 'cryptography' library.[/dim]"
    )


@main.command()
@click.option(
    "--token", required=True, envvar="TELEGRAM_BOT_TOKEN", help="Telegram Bot Token"
)
def bot(token):
    """Start the Telegram Bot (Polling Mode)."""
    from .bot_cli import run_bot

    console.print("[bold green]🤖 Starting Telegram Bot...[/bold green]")
    run_bot(token)


@main.command()
@click.option("--days", default=7, help="Retention days")
@click.option("--dir", default="data", help="Data directory")
def backup(days, dir):
    """Backup databases."""
    from .backup import backup_databases

    console.print("[yellow]Backing up databases...[/yellow]")
    backups = backup_databases(data_dir=dir, retention_days=days)
    for b in backups:
        console.print(f"[green]Backed up {b.name}[/green]")

@main.command()
def scan_dns():
    """Launch the interactive DNS Scanner TUI."""
    import subprocess
    import sys
    from pathlib import Path

    scanner_script = Path(__file__).parent / "tools" / "dns_scanner" / "python" / "dnsscanner_tui.py"
    
    if not scanner_script.exists():
        console.print(f"[bold red]Error: Scanner script not found at {scanner_script}[/bold red]")
        sys.exit(1)

    console.print(f"[green]Launching DNS Scanner TUI...[/green]")
    try:
        # Run using the same python interpreter
        subprocess.run([sys.executable, str(scanner_script)], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Scanner exited with error: {e}[/red]")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        console.print("\n[yellow]Scanner interrupted.[/yellow]")

if __name__ == "__main__":
    main()
