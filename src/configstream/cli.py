"""
Command Line Interface for ConfigStream.
"""

import asyncio
import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

from .pipeline import run_full_pipeline
from .geoip import DEFAULT_RESOLVER
from .tools.warp import generate_warp_proxy

# Initialize Rich Console
console = Console()


def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)],
    )
    # Silence noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


@click.group()
@click.version_option()
def main():
    """ConfigStream: Automated Proxy Aggregator & Tester"""


@main.command()
@click.option(
    "--sources", "-s", required=True, help="Path to sources file (local or URL list)"
)
@click.option("--output", "-o", default="output", help="Output directory")
@click.option("--max-workers", "-w", default=0, help="Concurrency limit (0=Auto-scale)")
@click.option("--timeout", "-t", default=10, help="Test timeout in seconds")
@click.option("--country", "-c", help="Filter by country code (e.g., US, DE)")
@click.option(
    "--max-latency", default=None, type=int, help="Maximum acceptable latency in ms"
)
@click.option(
    "--max-proxies", default=None, type=int, help="Limit number of tested proxies"
)
@click.option(
    "--leniency/--strict",
    default=False,
    help="Allow potentially insecure proxies (default: Strict)",
)
@click.option(
    "--dry-run", is_flag=True, help="Run without actual network calls (Simulation)"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def merge(
    sources,
    output,
    max_workers,
    timeout,
    country,
    max_latency,
    max_proxies,
    leniency,
    dry_run,
    verbose,
):
    """Fetch, test, and merge proxies from sources."""
    setup_logging(verbose)

    # Load sources
    source_path = Path(sources)
    if not source_path.exists():
        console.print(f"[red]Error: Sources file not found: {sources}[/red]")
        sys.exit(1)

    raw_sources = source_path.read_text(encoding="utf-8").splitlines()
    valid_sources = [
        s.strip() for s in raw_sources if s.strip() and not s.strip().startswith("#")
    ]

    console.print("[bold green]🚀 Starting ConfigStream Pipeline[/bold green]")
    console.print(f"Sources: {len(valid_sources)} | Output: {output}")

    async def _run():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:

            result = await run_full_pipeline(
                sources=valid_sources,
                output_dir=output,
                max_workers=max_workers,
                max_proxies=max_proxies,
                timeout=timeout,
                country_filter=country,
                max_latency=max_latency,
                leniency=leniency,
                progress=progress,
                dry_run=dry_run,
            )

            return result

    try:
        # Windows specific loop policy for asyncio + subprocesses
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        result = asyncio.run(_run())

        if result.success:
            stats = result.stats
            console.print(
                "\n[bold green]✨ Pipeline Completed Successfully![/bold green]"
            )
            console.print(f"⏱️ Duration: {stats['duration']:.1f}s")
            console.print(f"📥 Fetched: {stats['fetched_lines']}")
            console.print(f"🧪 Tested: {stats['tested']}")
            console.print(f"✅ Working: {stats['working']}")
            console.print(f"🌍 GeoIP: {stats['geo_resolved']}")
        else:
            console.print(f"\n[bold red]❌ Pipeline Failed: {result.error}[/bold red]")
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
    import subprocess

    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)

    console.print("[yellow]Downloading GeoIP databases...[/yellow]")

    # URLs for free GeoIP databases (FyraLabs mirror - updated daily)
    # Using GitHub releases for reliable access without MaxMind license
    base_url = "https://github.com/FyraLabs/geolite2/releases/latest/download"
    urls = {
        "GeoLite2-City.mmdb": f"{base_url}/GeoLite2-City.mmdb",
        "GeoLite2-ASN.mmdb": f"{base_url}/GeoLite2-ASN.mmdb",
    }

    success = True
    for name, url in urls.items():
        target = data_dir / name

        # Skip if already exists and is valid
        if target.exists() and target.stat().st_size > 0:
            size_mb = target.stat().st_size / (1024 * 1024)
            console.print(f"[green]✓ {name} already exists ({size_mb:.1f} MB)[/green]")
            continue

        console.print(f"[cyan]Downloading {name}...[/cyan]")

        try:
            result = subprocess.run(
                ["curl", "-L", "-o", str(target), url], capture_output=True, timeout=120
            )

            if result.returncode != 0:
                console.print(f"[red]Failed to download {name}[/red]")
                console.print(f"[dim]Error: {result.stderr.decode()}[/dim]")
                success = False
            elif not target.exists() or target.stat().st_size == 0:
                console.print(f"[red]Downloaded {name} is empty or missing[/red]")
                success = False
            else:
                size_mb = target.stat().st_size / (1024 * 1024)
                console.print(f"[green]✓ {name} ({size_mb:.1f} MB)[/green]")
        except subprocess.TimeoutExpired:
            console.print(f"[red]Download of {name} timed out[/red]")
            success = False
        except Exception as e:
            console.print(f"[red]Error downloading {name}: {e}[/red]")
            success = False

    if success:
        console.print("[bold green]✓ GeoIP databases updated successfully[/bold green]")
        sys.exit(0)
    else:
        console.print("[bold red]✗ Failed to download one or more databases[/bold red]")
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

    asyncio.run(_gen())

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


if __name__ == "__main__":
    main()
