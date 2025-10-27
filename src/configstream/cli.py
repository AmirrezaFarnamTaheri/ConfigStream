from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Sequence

import click
from rich.console import Console
from rich.progress import Progress

from . import pipeline
from .config import AppSettings
from .models import Proxy
from .geoip import download_geoip_dbs
from .logging_config import setup_logging
from .cli_errors import handle_cli_errors, CLIError

console = Console()
config = AppSettings()


# Error handling functions moved to cli_errors.py module


def validate_proxy_data(proxies_data: Sequence[object] | None, *, for_retest: bool = False) -> None:
    """Validate that proxy data is non-empty"""
    if not proxies_data or len(proxies_data) == 0:
        if for_retest:
            click.echo("No proxies found in the input file. Skipping retest.", err=False)
            # Exit gracefully for retest - don't fail the workflow
            raise SystemExit(0)
        click.echo("No proxies found in the input file.", err=True)
        sys.exit(1)


@click.group()
@click.version_option(version="1.0.0")
def cli() -> None:
    """
    ConfigStream: Automated VPN Configuration Aggregator.
    """
    setup_logging(config.LOG_LEVEL, config.MASK_SENSITIVE_DATA)


def _display_metrics(metrics: dict) -> None:
    if not metrics:
        return
    console.print("\n[cyan]Performance metrics[/cyan]")
    console.print(f"- Total time: {metrics.get('total_seconds', 0):.2f}s")
    console.print(f"- Fetch: {metrics.get('fetch_seconds', 0):.2f}s")
    console.print(f"- Parse: {metrics.get('parse_seconds', 0):.2f}s")
    console.print(f"- Test: {metrics.get('test_seconds', 0):.2f}s")
    console.print(f"- Geo: {metrics.get('geo_seconds', 0):.2f}s")
    console.print(f"- Output: {metrics.get('output_seconds', 0):.2f}s")
    console.print(f"- Proxies tested: {metrics.get('proxies_tested', 0)}")
    console.print(f"- Proxies working: {metrics.get('proxies_working', 0)}")
    console.print(f"- Throughput: {metrics.get('proxies_per_second', 0):.2f} proxies/s")


async def _merge_logic_async(
    sources_file: str,
    output_dir: str,
    max_proxies: int | None,
    country_filter: str | None,
    min_latency: int | None,
    max_latency: int | None,
    max_workers: int,
    timeout: int,
    show_metrics: bool,
    leniency: bool,
) -> None:
    # Download GeoIP databases
    console.print("Checking for GeoIP databases...")
    await download_geoip_dbs()

    # Resolve sources file (support running from packaged CLI or repo root)
    sources_path = Path(sources_file)
    if not sources_path.exists():
        fallback = Path(__file__).resolve().parents[2] / sources_file
        if fallback.exists():
            sources_path = fallback
        else:
            raise CLIError(f"Sources file not found: {sources_file}")

    sources = sources_path.read_text().splitlines()
    sources = [s.strip() for s in sources if s.strip() and not s.startswith("#")]

    if not sources:
        raise CLIError("No sources found in the specified file.")

    click.echo(f"Loaded {len(sources)} sources")

    # Run pipeline
    with Progress() as progress:
        result = await pipeline.run_full_pipeline(
            sources,
            output_dir,
            progress,
            max_workers=max_workers,
            max_proxies=max_proxies,
            min_latency=min_latency,
            max_latency=max_latency,
            timeout=timeout,
            country_filter=country_filter,
            leniency=leniency,
        )

    if not result["success"]:
        error_msg = result.get("error")
        if not error_msg:
            kept = result.get("kept")
            if kept == 0:
                error_msg = "no proxies met the acceptance criteria"
            else:
                error_msg = "unknown error"
        raise CLIError(f"Pipeline failed: {error_msg}")

    click.echo("\n Pipeline completed successfully!")
    click.echo(f"Output files saved to: {output_dir}")

    if show_metrics:
        _display_metrics(result.get("metrics") or {})


@cli.command()
@click.option(
    "--sources", "sources_file", required=True, type=click.Path(exists=True, dir_okay=False)
)
@click.option("--output", "output_dir", default="output", type=click.Path(file_okay=False))
@click.option("--max-proxies", type=int)
@click.option("--country", "country_filter", type=str)
@click.option("--min-latency", type=int)
@click.option("--max-latency", type=int, default=5000)
@click.option("--max-workers", type=int, default=25)
@click.option("--timeout", type=int, default=10)
@click.option("--show-metrics", is_flag=True)
@click.option("--leniency", is_flag=True, help="Disable security filtering for debugging.")
@handle_cli_errors(context="Merge operation")
def merge(
    sources_file: str,
    output_dir: str,
    max_proxies: int,
    country_filter: str | None,
    min_latency: int | None,
    max_latency: int | None,
    max_workers: int,
    timeout: int,
    show_metrics: bool,
    leniency: bool,
) -> None:
    """Run the full pipeline: fetch, test, and generate outputs."""
    asyncio.run(
        _merge_logic_async(
            sources_file=sources_file,
            output_dir=output_dir,
            max_proxies=max_proxies,
            country_filter=country_filter,
            min_latency=min_latency,
            max_latency=max_latency,
            max_workers=max_workers,
            timeout=timeout,
            show_metrics=show_metrics,
            leniency=leniency,
        )
    )


async def _update_databases_logic_async() -> None:
    console.print("Updating GeoIP databases...")
    success = await download_geoip_dbs()
    if success:
        console.print("✅ All databases updated successfully!")
    else:
        console.print("❌ Some databases failed to update.")
        console.print("   Check MAXMIND_LICENSE_KEY environment variable or GitHub secret.")


@cli.command()
def update_databases() -> None:
    """Update GeoIP databases for proxy geolocation."""
    asyncio.run(_update_databases_logic_async())


async def _retest_logic_async(
    input_file: str,
    output_dir: str,
    max_workers: int,
    timeout: int,
    show_metrics: bool,
    leniency: bool,
) -> None:
    # Set event loop policy for Windows compatibility
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    input_path = Path(input_file)
    output_path = Path(output_dir)

    # Check if input file exists and is not empty
    if not input_path.exists():
        click.echo(f"Input file {input_path} does not exist. Skipping retest.", err=False)
        raise SystemExit(0)

    if input_path.stat().st_size == 0:
        click.echo(f"Input file {input_path} is empty. Skipping retest.", err=False)
        raise SystemExit(0)

    # Load JSON from file
    try:
        with open(input_path, "r") as f:
            proxies_data = json.load(f)
    except json.JSONDecodeError as e:
        click.echo(f"Invalid JSON in {input_path}: {e}. Skipping retest.", err=False)
        raise SystemExit(0)

    # Validate we have proxies
    validate_proxy_data(proxies_data, for_retest=True)
    click.echo(f"Loaded {len(proxies_data)} proxies")

    # Reconstruct Proxy objects from JSON data
    proxies: list[Proxy] = []
    skipped_count = 0

    for proxy_data in proxies_data:
        try:
            proxy = Proxy(**proxy_data)
            proxies.append(proxy)
        except (TypeError, ValueError):
            skipped_count += 1

    if skipped_count > 0:
        click.echo(f"⚠ Skipped {skipped_count} invalid proxy definitions")

    if not proxies:
        raise CLIError("No proxies found in the input file.")

    click.echo(f" Validated {len(proxies)} proxy definitions")

    # Run retest pipeline
    output_path.mkdir(parents=True, exist_ok=True)

    with Progress() as progress:
        result = await pipeline.run_full_pipeline(
            sources=[],
            output_dir=str(output_path),
            progress=progress,
            max_workers=max_workers,
            proxies=proxies,
            timeout=timeout,
            leniency=leniency,
        )

    if not result.get("success", True):
        error_msg = result.get("error", "Retest failed")
        raise CLIError(error_msg)

    click.echo("\n Retest completed successfully!")
    click.echo(f"Output files saved to: {output_path}")

    if show_metrics:
        _display_metrics(result.get("metrics") or {})


@cli.command()
@click.option(
    "--input", "input_file", default="output/proxies.json", type=click.Path(dir_okay=False)
)
@click.option("--output", "output_dir", default="output", type=click.Path(file_okay=False))
@click.option("--max-workers", type=int, default=10)
@click.option("--timeout", type=int, default=30)
@click.option(
    "--lenient/--no-lenient",
    default=True,
    help="Keep insecure configs but tag them (default: lenient).",
)
@click.option("--show-metrics", is_flag=True)
@handle_cli_errors(context="Retest operation")
def retest(
    input_file: str,
    output_dir: str,
    max_workers: int,
    timeout: int,
    lenient: bool,
    show_metrics: bool,
) -> None:
    """Retest previously tested proxies from a JSON file."""
    asyncio.run(
        _retest_logic_async(
            input_file=input_file,
            output_dir=output_dir,
            max_workers=max_workers,
            timeout=timeout,
            show_metrics=show_metrics,
            leniency=lenient,
        )
    )


def main() -> None:
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":  # pragma: no cover - module execution convenience
    main()
