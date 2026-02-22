# SPDX-License-Identifier: AGPL-3.0-or-later
import shutil
import tarfile
import httpx
import click
from rich.console import Console
from pathlib import Path
import sys
from .logging_config import setup_logging

console = Console()


@click.group()
def main():
    """ConfigStream CLI Tool."""
    pass


@main.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def run(verbose):
    """Run the full ConfigStream pipeline."""
    from .pipeline import Pipeline
    from .config import AppSettings
    import asyncio

    setup_logging(level="DEBUG" if verbose else "INFO")

    console.print("[bold green]Starting ConfigStream Pipeline...[/bold green]")

    try:
        pipeline = Pipeline()
        # Ensure we run in an async loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(pipeline.run())
        loop.close()

        if result.success:
            console.print(
                f"\n[bold green]Pipeline Completed Successfully![/bold green]"
            )
            console.print(f"Parsed: {result.stats.parsed}")
            console.print(f"Tested: {result.stats.tested}")
            console.print(f"Working: {result.stats.working}")
            console.print(f"Revived: {result.stats.total_revived}")

            if not result.stats.working and not AppSettings().FAIL_ON_ZERO_WORKING:
                 console.print(
                        "[yellow]Continuing despite 0 working proxies (FAIL_ON_ZERO_WORKING=False)[/yellow]"
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
        # if DEFAULT_RESOLVER:
        #     DEFAULT_RESOLVER.close()
        pass


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

    def stream_download(url: str, target: Path) -> bool:
        safe_url = SecurityValidator.sanitize_log_message(url)
        try:
            with httpx.stream("GET", url, timeout=120, follow_redirects=True) as resp:
                if resp.status_code != 200:
                    console.print(
                        f"[red]HTTP {resp.status_code} while fetching {safe_url}[/red]"
                    )
                    return False
                with target.open("wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=8192):
                        f.write(chunk)
            return target.exists() and target.stat().st_size > 0
        except httpx.RequestError as exc:
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
    # Lazy import to avoid circular dependency
    from .generators.warp import generate_warp_proxy

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
    import subprocess  # nosec
    import sys
    from pathlib import Path

    scanner_script = (
        Path(__file__).parent / "tools" / "dns_scanner" / "python" / "dnsscanner_tui.py"
    )

    if not scanner_script.exists():
        console.print(
            f"[bold red]Error: Scanner script not found at {scanner_script}[/bold red]"
        )
        sys.exit(1)

    console.print("[green]Launching DNS Scanner TUI...[/green]")
    try:
        subprocess.run([sys.executable, str(scanner_script)], check=True)  # nosec
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Scanner exited with error: {e}[/red]")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        console.print("\n[yellow]Scanner interrupted.[/yellow]")


if __name__ == "__main__":
    main()
