#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Standalone DNS Scanner
Scans IPs/CIDRs for working DNS servers using aiodns.
Based on dnsscanner_tui.py logic but adapted for CLI.
"""
import logging

import asyncio
import ipaddress
import sys
import time
import secrets
import aiodns
from pathlib import Path
from typing import List, Tuple
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)

console = Console()


async def test_dns(
    ip: str, domain: str, timeout: float = 2.0
) -> Tuple[str, bool, float]:
    """Test if IP is a working DNS server."""
    try:
        resolver = aiodns.DNSResolver(nameservers=[ip], timeout=timeout, tries=1)
        start = time.time()
        try:
            await resolver.query(domain, "A")
            elapsed = time.time() - start
            return (ip, True, elapsed)
        except aiodns.error.DNSError as e:
            # Check for error codes that imply the server IS a DNS server (just returned error)
            # 1=NXDOMAIN, 3=NXRRSET, 4=NODATA
            error_code = e.args[0] if e.args else 0
            if error_code in (1, 3, 4):
                elapsed = time.time() - start
                return (ip, True, elapsed)
            return (ip, False, 0.0)
    except Exception:
        logging.getLogger(__name__).debug("Suppressed broad exception", exc_info=True)
        return (ip, False, 0.0)


async def scan_cidrs(
    cidrs: List[str], concurrency: int = 100, output_file: str = "dns_results.txt"
):
    """Scan IPs generated from CIDRs."""

    ips = []
    console.print(f"[cyan]Generating IPs from {len(cidrs)} CIDRs...[/cyan]")
    for cidr in cidrs:
        try:
            net = ipaddress.IPv4Network(cidr, strict=False)
            if net.num_addresses > 65536:
                console.print(
                    f"[yellow]Skipping large subnet {cidr} (>65k IPs)[/yellow]"
                )
                continue
            for ip in net.hosts():
                ips.append(str(ip))
        except Exception as e:
            console.print(f"[red]Invalid CIDR {cidr}: {e}[/red]")

    # Shuffle for better distribution
    rng = secrets.SystemRandom()
    rng.shuffle(ips)

    total_ips = len(ips)
    console.print(
        f"[green]Starting scan on {total_ips} IPs with {concurrency} concurrency...[/green]"
    )

    sem = asyncio.Semaphore(concurrency)
    found_servers = []

    async def worker(ip):
        async with sem:
            result = await test_dns(ip, "google.com")
            return result

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Scanning...", total=total_ips)

        # Chunking to avoid massive memory usage with gather
        chunk_size = 1000
        for i in range(0, total_ips, chunk_size):
            chunk = ips[i : i + chunk_size]
            coros = [worker(ip) for ip in chunk]
            results = await asyncio.gather(*coros)

            for ip, success, lat in results:
                if success:
                    found_servers.append((ip, lat))
                    # console.print(f"[green]Found: {ip} ({lat*1000:.0f}ms)[/green]")

            progress.update(
                task,
                advance=len(chunk),
                description=f"[cyan]Scanning... Found: {len(found_servers)}",
            )

    # Save results
    found_servers.sort(key=lambda x: x[1])
    with open(output_file, "w") as f:
        f.write("# DNS Scanner Results\n")
        f.write(f"# Scanned: {total_ips} | Found: {len(found_servers)}\n")
        for ip, lat in found_servers:
            f.write(f"{ip}\t# {lat*1000:.0f}ms\n")

    console.print(
        f"[bold green]Scan Complete! Found {len(found_servers)} servers. Saved to {output_file}[/bold green]"
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("Usage: python3 dns_scanner.py <cidr_file_or_cidr> [concurrency]")
        sys.exit(1)

    input_arg = sys.argv[1]
    concurrency = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    cidrs = []
    if Path(input_arg).exists():
        with open(input_arg, "r") as f:
            cidrs = [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
    else:
        cidrs = [input_arg]

    asyncio.run(scan_cidrs(cidrs, concurrency))
