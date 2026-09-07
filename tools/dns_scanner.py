#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Standalone asynchronous IPv4 DNS resolver scanner."""

from __future__ import annotations

import asyncio
import ipaddress
import secrets
import sys
import time
from collections.abc import Iterable
from pathlib import Path

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
MAX_CIDR_INPUTS = 4096
MAX_ADDRESSES_PER_CIDR = 65536
MAX_TOTAL_TARGETS = 250_000
TEST_DOMAIN = "example.com"


async def test_dns(
    ip: str, domain: str, timeout: float = 2.0
) -> tuple[str, bool, float]:
    """Return success only when the resolver returns an actual A-record answer."""

    try:
        resolver = aiodns.DNSResolver(nameservers=[ip], timeout=timeout, tries=1)
        start = time.perf_counter()
        answer = await resolver.query(domain, "A")
    except (aiodns.error.DNSError, OSError, ValueError):
        # Resolver setup failures and completed DNS errors prove only that this
        # address is not a useful recursive resolver for the known-good domain.
        return (ip, False, 0.0)

    elapsed = time.perf_counter() - start
    if not answer:
        return (ip, False, 0.0)
    return (ip, True, elapsed)


def _usable_host_count(network: ipaddress.IPv4Network) -> int:
    """Return the number of addresses produced by ``IPv4Network.hosts()``."""

    if network.prefixlen >= 31:
        return network.num_addresses
    return max(0, network.num_addresses - 2)


async def scan_cidrs(
    cidrs: Iterable[str],
    concurrency: int = 100,
    output_file: str = "dns_results.txt",
) -> None:
    """Scan IPv4 addresses generated from CIDRs within explicit input budgets."""

    if concurrency < 1:
        raise ValueError("concurrency must be at least 1")
    if concurrency > CHUNK_SIZE:
        raise ValueError(
            f"concurrency cannot exceed the scanner chunk size ({CHUNK_SIZE})"
        )

    ips: list[str] = []
    cidr_count = 0
    target_count = 0
    console.print("[cyan]Generating IPs from CIDRs...[/cyan]")
    for cidr in cidrs:
        cidr_count += 1
        if cidr_count > MAX_CIDR_INPUTS:
            raise ValueError(
                f"CIDR input budget exceeded ({MAX_CIDR_INPUTS} entries maximum)"
            )
        try:
            net = ipaddress.IPv4Network(cidr, strict=False)
            if net.num_addresses > MAX_ADDRESSES_PER_CIDR:
                console.print(
                    f"[yellow]Skipping large subnet {cidr} "
                    f"(>{MAX_ADDRESSES_PER_CIDR} IPs)[/yellow]"
                )
                continue
            network_targets = _usable_host_count(net)
            if target_count + network_targets > MAX_TOTAL_TARGETS:
                raise ValueError(
                    f"DNS target budget exceeded ({MAX_TOTAL_TARGETS} addresses maximum)"
                )
            target_count += network_targets
            ips.extend(str(address) for address in net.hosts())
        except (
            ipaddress.AddressValueError,
            ipaddress.NetmaskValueError,
        ) as exc:
            console.print(f"[red]Invalid CIDR {cidr}: {exc}[/red]")

    rng = secrets.SystemRandom()
    rng.shuffle(ips)

    total_ips = len(ips)
    console.print(
        f"[green]Starting scan on {total_ips} IPs from {cidr_count} CIDRs "
        f"with {concurrency} concurrency...[/green]"
    )

    sem = asyncio.Semaphore(concurrency)
    found_servers: list[tuple[str, float]] = []

    async def worker(ip: str) -> tuple[str, bool, float]:
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

            for result_ip, success, latency in results:
                if success:
                    found_servers.append((result_ip, latency))

            progress.update(
                task,
                advance=len(chunk),
                description=f"[cyan]Scanning... Found: {len(found_servers)}",
            )

    found_servers.sort(key=lambda item: item[1])
    with Path(output_file).open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# DNS Scanner Results\n")
        handle.write(f"# Scanned: {total_ips} | Found: {len(found_servers)}\n")
        for server_ip, latency in found_servers:
            handle.write(f"{server_ip}\t# {latency * 1000:.0f}ms\n")

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
            cidrs = (
                line.strip()
                for line in handle
                if line.strip() and not line.lstrip().startswith("#")
            )
            asyncio.run(scan_cidrs(cidrs, concurrency))
    else:
        asyncio.run(scan_cidrs([input_arg], concurrency))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
