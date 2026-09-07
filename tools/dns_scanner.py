#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Standalone asynchronous IPv4 DNS resolver scanner."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import secrets
import sys
import time
from pathlib import Path
from typing import List, Tuple

import aiodns
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

console = Console()
CHUNK_SIZE = 1000
TEST_DOMAIN = "example.com"


async def test_dns(
    ip: str, domain: str, timeout: float = 2.0
) -> Tuple[str, bool, float]:
    """Return success only when the resolver returns an actual A-record answer."""

    try:
        resolver = aiodns.DNSResolver(nameservers=[ip], timeout=timeout, tries=1)
        start = time.perf_counter()
        try:
            answer = await resolver.query(domain, "A")
        except aiodns.error.DNSError:
            # A completed DNS error (for example ENODATA, SERVFAIL, ENOTFOUND,
            # REFUSED) proves only that something answered the query. It does not
            # prove that this address is a useful recursive resolver for the
            # scanner's known-good domain.
            return (ip, False, 0.0)
        elapsed = time.perf_counter() - start
        if not answer:
            return (ip, False, 0.0)
        return (ip, True, elapsed)
    except Exception:
        logging.getLogger(__name__).debug("DNS probe failed", exc_info=True)
        return (ip, False, 0.0)


async def scan_cidrs(
    cidrs: List[str], concurrency: int = 100, output_file: str = "dns_results.txt"
) -> None:
    """Scan IPv4 addresses generated from CIDRs."""

    if concurrency < 1:
        raise ValueError("concurrency must be at least 1")
    if concurrency > CHUNK_SIZE:
        raise ValueError(
            f"concurrency cannot exceed the scanner chunk size ({CHUNK_SIZE})"
        )

    ips: list[str] = []
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
        except (ipaddress.AddressValueError, ipaddress.NetmaskValueError, ValueError) as exc:
            console.print(f"[red]Invalid CIDR {cidr}: {exc}[/red]")

    rng = secrets.SystemRandom()
    rng.shuffle(ips)

    total_ips = len(ips)
    console.print(
        f"[green]Starting scan on {total_ips} IPs with {concurrency} concurrency...[/green]"
    )

    sem = asyncio.Semaphore(concurrency)
    found_servers: list[tuple[str, float]] = []

    async def worker(ip: str) -> Tuple[str, bool, float]:
        async with sem:
            return await test_dns(ip, TEST_DOMAIN)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Scanning...", total=total_ips)

        for i in range(0, total_ips, CHUNK_SIZE):
            chunk = ips[i : i + CHUNK_SIZE]
            results = await asyncio.gather(*(worker(ip) for ip in chunk))

            for ip, success, latency in results:
                if success:
                    found_servers.append((ip, latency))

            progress.update(
                task,
                advance=len(chunk),
                description=f"[cyan]Scanning... Found: {len(found_servers)}",
            )

    found_servers.sort(key=lambda item: item[1])
    with Path(output_file).open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# DNS Scanner Results\n")
        handle.write(f"# Scanned: {total_ips} | Found: {len(found_servers)}\n")
        for ip, latency in found_servers:
            handle.write(f"{ip}\t# {latency * 1000:.0f}ms\n")

    console.print(
        f"[bold green]Scan Complete! Found {len(found_servers)} servers. "
        f"Saved to {output_file}[/bold green]"
    )


def _parse_concurrency(raw: str | None) -> int:
    if raw is None:
        return 100
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit("concurrency must be an integer") from exc
    if not 1 <= value <= CHUNK_SIZE:
        raise SystemExit(f"concurrency must be between 1 and {CHUNK_SIZE}")
    return value


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        console.print("Usage: python3 dns_scanner.py <cidr_file_or_cidr> [concurrency]")
        return 1

    input_arg = args[0]
    concurrency = _parse_concurrency(args[1] if len(args) > 1 else None)
    if len(args) > 2:
        raise SystemExit("too many arguments")

    input_path = Path(input_arg)
    if input_path.is_file():
        with input_path.open("r", encoding="utf-8") as handle:
            cidrs = [
                line.strip()
                for line in handle
                if line.strip() and not line.lstrip().startswith("#")
            ]
    else:
        cidrs = [input_arg]

    asyncio.run(scan_cidrs(cidrs, concurrency))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
