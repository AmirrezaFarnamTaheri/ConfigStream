# SPDX-License-Identifier: AGPL-3.0-or-later
import sys
import asyncio
import logging
import os
import tarfile
import tempfile
from pathlib import Path

import click
import httpx
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

from .pipeline.core import run_full_pipeline
from .source_admission import (
    SourceAdmissionError,
    partition_fetchable_sources,
    resolve_source_admission_manifest,
)

# Initialize Rich Console
console = Console()


async def generate_warp_proxy():
    """Lazy compatibility seam for WARP generation."""
    from .tools.warp import generate_warp_proxy as implementation

    return await implementation()


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )
    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


@click.group()
@click.version_option()
def main():
    """ConfigStream CLI - High-performance proxy aggregator and tester."""
    pass


@main.command()
@click.option("--sources", required=True, help="Path to sources.txt")
@click.option("--output", default="output", help="Output directory")
@click.option("--max-workers", default=50, help="Max concurrent workers")
@click.option("--timeout", type=float, help="Test timeout in seconds")
@click.option("--country", help="Filter by country code (e.g., US)")
@click.option("--max-latency", type=int, help="Max latency in ms")
@click.option("--leniency", is_flag=True, help="Enable lenient testing mode")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Skip network proxy tests (still fetches/parses sources and generates outputs)",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Fail the pipeline strictly if 0 working proxies are found.",
)
@click.option(
    "--allow-unadmitted-sources",
    is_flag=True,
    help=(
        "Allow source URLs that are not present in the reviewed admission manifest. "
        "Use only for explicit local experiments."
    ),
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable debug logging",
)
def merge(
    sources,
    output,
    max_workers,
    timeout,
    country,
    max_latency,
    leniency,
    dry_run,
    strict,
    allow_unadmitted_sources,
    verbose,
):
    """Fetch, test, and merge proxies from sources."""
    setup_logging(verbose)
    from .config import AppSettings

    settings = AppSettings()
    if timeout is None:
        timeout = settings.TEST_TIMEOUT

    # Load sources
    source_path = Path(sources)
    if not source_path.exists():
        console.print(f"[red]Error: Sources file not found: {sources}[/red]")
        sys.exit(1)

    raw_sources = source_path.read_text(encoding="utf-8").splitlines()
    valid_sources = [
        s.strip() for s in raw_sources if s.strip() and not s.strip().startswith("#")
    ]

    if settings.ENFORCE_SOURCE_ADMISSION and not allow_unadmitted_sources:
        try:
            accepted_sources, blocked_sources = partition_fetchable_sources(
                valid_sources,
                manifest_path=resolve_source_admission_manifest(
                    settings.SOURCE_ADMISSION_MANIFEST
                ),
            )
        except (OSError, ValueError, SourceAdmissionError) as exc:
            console.print(f"[red]Source admission failed: {exc}[/red]")
            sys.exit(2)
        valid_sources = [entry.url for entry in accepted_sources]
        if blocked_sources:
            console.print(
                "[yellow]Source admission skipped "
                f"{len(blocked_sources)} insecure-transport source(s).[/yellow]"
            )
        if not valid_sources:
            console.print("[red]Source admission left no fetchable sources.[/red]")
            sys.exit(2)
    elif settings.ENFORCE_SOURCE_ADMISSION:
        console.print(
            "[yellow]Warning: source admission was explicitly bypassed for this run.[/yellow]"
        )

    console.print("[bold green]🚀 Starting Config's Stream[/bold green]")
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
                timeout=timeout,
                country_filter=country,
                max_latency=max_latency,
                leniency=leniency,
                progress=progress,
                dry_run=dry_run,
                time_limit_seconds=settings.BATCH_TIME_LIMIT_SECONDS,
            )

            return result

    try:
        # Windows specific loop policy for asyncio + subprocesses
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        coro = _run()
        try:
            result = asyncio.run(coro)
        except RuntimeError as e:
            coro.close()
            if "no current event loop" in str(e).lower():
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(_run())
                finally:
                    loop.close()
                    asyncio.set_event_loop(None)
            else:
                raise

        if result.success:
            stats_obj = result.stats
            # Handle both object and dict (depending on pipeline run type)

            def _get(key):
                if hasattr(stats_obj, key):
                    return getattr(stats_obj, key)
                if isinstance(stats_obj, dict):
                    return stats_obj.get(key, 0)
                return 0

            console.print("\n[bold green]Pipeline Completed Successfully![/bold green]")
            console.print(f"Duration: {_get('duration'):.1f}s")
            console.print(f"Fetched: {_get('fetched_lines')}")
            console.print(f"Tested: {_get('tested')}")
            console.print(f"Working: {_get('working')}")
            console.print(f"GeoIP: {_get('geo_resolved')}")

            time_limited = False
            if hasattr(stats_obj, "time_limited"):
                time_limited = bool(stats_obj.time_limited)
            elif isinstance(stats_obj, dict):
                time_limited = bool(stats_obj.get("time_limited", False))

            if time_limited:
                console.print(
                    "[yellow]Time limit reached; output contains partial results.[/yellow]"
                )

            # CRITICAL: Fail pipeline if zero working proxies found
            # This ensures GitHub Actions workflow fails instead of silently passing with empty results.
            working = _get("working")
            if working == 0:
                console.print(
                    "\n[bold red]CRITICAL: Pipeline finished with 0 working proxies![/bold red]"
                )
                if (
                    strict or getattr(settings, "FAIL_ON_ZERO_WORKING", False)
                ) and not time_limited:
                    sys.exit(1)
                else:
                    console.print(
                        "[yellow]Continuing despite 0 working proxies (strict=False or time_limited=True)[/yellow]"
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
        # GeoIP support is optional for commands such as ``update-databases``.
        # Import it only after the merge path has used the resolver.
        try:
            from .geoip import DEFAULT_RESOLVER
        except ImportError:
            DEFAULT_RESOLVER = None
        if DEFAULT_RESOLVER:
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

    max_download_bytes = 256 * 1024 * 1024

    def stream_download(url: str, target: Path) -> bool:
        """Download to a sibling temporary file and publish only on completion."""
        safe_url = SecurityValidator.sanitize_log_message(url)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
        os.close(fd)
        temp_path = Path(temp_name)
        try:
            with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as resp:
                if resp.status_code != 200:
                    console.print(
                        f"[red]HTTP {resp.status_code} while fetching {safe_url}[/red]"
                    )
                    return False
                content_length = getattr(resp, "headers", {}).get("content-length")
                if content_length:
                    try:
                        if int(content_length) > max_download_bytes:
                            raise ValueError("download exceeds the database size limit")
                    except ValueError as exc:
                        raise ValueError("invalid or excessive Content-Length") from exc
                total = 0
                with temp_path.open("wb") as handle:
                    for chunk in resp.iter_bytes(chunk_size=8192):
                        if not chunk:
                            continue
                        total += len(chunk)
                        if total > max_download_bytes:
                            raise ValueError("download exceeds the database size limit")
                        handle.write(chunk)
                if total == 0:
                    raise ValueError("download produced an empty file")
            os.replace(temp_path, target)
            return True
        except (httpx.HTTPError, OSError, ValueError) as exc:
            safe_exc = SecurityValidator.sanitize_log_message(str(exc))
            console.print(f"[red]Download failed for {safe_url}: {safe_exc}[/red]")
            return False
        finally:
            temp_path.unlink(missing_ok=True)

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
                if extracted is None or member.size <= 0:
                    console.print(f"[red]Archive entry for {edition} is empty[/red]")
                    return False
                if member.size > max_download_bytes:
                    console.print(
                        f"[red]Archive entry for {edition} is too large[/red]"
                    )
                    return False
                fd, temp_name = tempfile.mkstemp(
                    prefix=f".{target.name}.", dir=target.parent
                )
                os.close(fd)
                temp_target = Path(temp_name)
                try:
                    with temp_target.open("wb") as dest:
                        remaining = member.size
                        while remaining:
                            chunk = extracted.read(min(1024 * 1024, remaining))
                            if not chunk:
                                raise OSError(
                                    "archive entry ended before its declared size"
                                )
                            dest.write(chunk)
                            remaining -= len(chunk)
                    os.replace(temp_target, target)
                finally:
                    temp_target.unlink(missing_ok=True)
            return target.exists() and target.stat().st_size > 0
        except (OSError, tarfile.TarError, ValueError) as exc:
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
    console.print(
        "[yellow]Downloading Sing-box databases (geosite.db, geoip.db)...[/yellow]"
    )
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
            console.print(
                f"[green]OK {db_name} already exists ({size_mb:.1f} MB)[/green]"
            )
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
        console.print(
            "[yellow]GeoIP databases updated, but Sing-box databases failed[/yellow]"
        )
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
            console.print(f"\n[bold green]Config #{i + 1}:[/bold green]")
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


@main.command(
    deprecated=True,
    epilog=(
        "This command is deprecated and will be removed in a future release. "
        "Active DNS scanning was disabled to comply with the ConfigStream "
        "no-third-party-scanning policy. See the wiki for alternatives."
    ),
)
def scan_dns():
    """[DEPRECATED] Launch the interactive DNS Scanner TUI.

    This command no longer performs any scanning. It is retained only for
    backwards-compatibility with existing scripts and will be removed in the
    next major release (S-4 governance).
    """
    console.print(
        "[bold yellow]scan_dns is deprecated and does nothing.[/bold yellow]\n"
        "[yellow]Active DNS scanning has been disabled to comply with the "
        "ConfigStream no-third-party-scanning policy.[/yellow]"
    )


if __name__ == "__main__":
    main()
