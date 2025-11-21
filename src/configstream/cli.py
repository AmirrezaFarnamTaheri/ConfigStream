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
from .geoip_offline import DEFAULT_RESOLVER
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
def main():
    """ConfigStream: Automated Proxy Aggregator & Tester"""
    pass


@main.command()
@click.option(
    "--sources", "-s", required=True, help="Path to sources file (local or URL list)"
)
@click.option("--output", "-o", default="output", help="Output directory")
@click.option("--max-workers", "-w", default=0, help="Concurrency limit (0=Auto-scale)")
@click.option("--timeout", "-t", default=10, help="Test timeout in seconds")
@click.option("--country", "-c", help="Filter by country code (e.g., US, DE)")
@click.option("--min-latency", default=None, type=int, help="Minimum latency in ms")
@click.option(
    "--max-proxies", default=None, type=int, help="Limit number of tested proxies"
)
@click.option(
    "--leniency/--strict",
    default=False,
    help="Allow potentially insecure proxies (default: Strict)",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def merge(
    sources,
    output,
    max_workers,
    timeout,
    country,
    min_latency,
    max_proxies,
    leniency,
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
                min_latency=min_latency,
                leniency=leniency,
                progress=progress,
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
    console.print(
        "[yellow]This feature is handled by the CI/CD workflow or manual download.[/yellow]"
    )
    console.print(
        "Please place GeoLite2-City.mmdb and GeoLite2-ASN.mmdb in the 'data/' directory."
    )


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
