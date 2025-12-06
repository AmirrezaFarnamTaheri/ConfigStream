#!/usr/bin/env python3
"""
ConfigStream Pipeline Health Check

Verifies pipeline outputs meet quality standards.
Exits with code 0 if healthy, 1 if unhealthy.

Usage:
    python scripts/healthcheck.py --min-proxies 100 --min-success-rate 0.3
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any


class HealthCheckError(Exception):
    """Health check failure."""


def check_file_exists(file_path: Path, name: str) -> None:
    """Check if required file exists."""
    if not file_path.exists():
        raise HealthCheckError(f"❌ {name} not found: {file_path}")
    print(f"✓ {name} exists: {file_path}")


def check_minimum_proxies(proxies: List[Dict], min_count: int) -> None:
    """Check minimum proxy count."""
    count = len(proxies)
    if count < min_count:
        raise HealthCheckError(f"❌ Only {count} proxies found (minimum: {min_count})")
    print(f"✓ Proxy count: {count} (minimum: {min_count})")


def check_success_rate(metadata: Dict[str, Any], min_rate: float) -> None:
    """Check proxy test success rate."""
    # Compatible with both new and old metadata formats
    # Use parsed count if available, otherwise fetched
    tested = metadata.get("stats", {}).get(
        "parsed", metadata.get("total_fetched", metadata.get("total_proxies_tested", 0))
    )
    working = metadata.get("total_working", metadata.get("total_working_proxies", 0))

    # Validate metrics before division
    if not isinstance(tested, (int, float)) or tested < 0:
        raise HealthCheckError(f"❌ Invalid tested count: {tested}")

    if not isinstance(working, (int, float)) or working < 0:
        raise HealthCheckError(f"❌ Invalid working count: {working}")

    if tested == 0:
        if working > 0:
            print(f"⚠️  'tested' count missing or zero, but {working} working proxies found. Skipping success rate check.")
            return
        raise HealthCheckError("❌ No proxies tested")

    if working > tested:
        raise HealthCheckError(
            f"❌ Working proxies ({working}) exceeds tested ({tested})"
        )

    success_rate = working / tested

    if success_rate < min_rate:
        raise HealthCheckError(
            f"❌ Success rate too low: {success_rate:.1%} (minimum: {min_rate:.1%})"
        )

    print(f"✓ Success rate: {success_rate:.1%} (minimum: {min_rate:.1%})")


def check_data_freshness(metadata: Dict[str, Any], max_age_hours: int) -> None:
    """Check data freshness."""
    timestamp_str = metadata.get("last_updated_utc", metadata.get("timestamp"))

    if not timestamp_str:
        raise HealthCheckError("❌ No timestamp in metadata")

    try:
        last_run = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        age = datetime.now(last_run.tzinfo) - last_run

        if age > timedelta(hours=max_age_hours):
            raise HealthCheckError(
                f"❌ Data is stale: {age.total_seconds() / 3600:.1f}h old "
                f"(maximum: {max_age_hours}h)"
            )

        print(
            f"✓ Data freshness: {age.total_seconds() / 3600:.1f}h old "
            f"(maximum: {max_age_hours}h)"
        )

    except Exception as e:
        raise HealthCheckError(f"❌ Failed to parse timestamp: {e}") from e


def check_protocol_diversity(proxies: List[Dict], min_protocols: int) -> None:
    """Check protocol diversity."""
    protocols = set()
    for p in proxies:
        proto = p.get("protocol")
        if isinstance(proto, str) and proto.strip():
            protocols.add(proto.strip().lower())

    if len(protocols) < min_protocols:
        raise HealthCheckError(
            f"❌ Low protocol diversity: {len(protocols)} protocols (minimum: {min_protocols})"
        )

    print(
        f"✓ Protocol diversity: {len(protocols)} protocols (minimum: {min_protocols})"
    )
    print(f"  Protocols: {', '.join(sorted(protocols))}")


def check_geographic_diversity(proxies: List[Dict], min_countries: int) -> None:
    """Check geographic diversity."""
    countries = set(
        p.get("country_code")
        for p in proxies
        if p.get("country_code") and p.get("is_working")
    )

    if len(countries) < min_countries:
        raise HealthCheckError(
            f"❌ Low geographic diversity: {len(countries)} countries "
            f"(minimum: {min_countries})"
        )

    print(
        f"✓ Geographic diversity: {len(countries)} countries (minimum: {min_countries})"
    )


def check_average_latency(proxies: List[Dict], max_avg_latency: int) -> None:
    """Check average latency of working proxies."""
    working_proxies = [
        p for p in proxies if p.get("is_working") and p.get("latency") is not None
    ]

    if not working_proxies:
        raise HealthCheckError("❌ No working proxies with latency data")

    latencies = []
    for p in working_proxies:
        val = p.get("latency")
        if val is None:
            continue
        try:
            num = float(val)
        except (TypeError, ValueError):
            continue
        if num < 0 or not (num == num):  # exclude negatives and NaN
            continue
        latencies.append(num)

    if not latencies:
        raise HealthCheckError("❌ No valid latency samples for working proxies")

    avg_latency = sum(latencies) / len(latencies)

    if avg_latency > max_avg_latency:
        raise HealthCheckError(
            f"❌ Average latency too high: {avg_latency:.0f}ms "
            f"(maximum: {max_avg_latency}ms)"
        )

    print(f"✓ Average latency: {avg_latency:.0f}ms " f"(maximum: {max_avg_latency}ms)")


def run_health_checks(
    output_dir: Path,
    min_proxies: int,
    min_success_rate: float,
    max_age_hours: int,
    min_protocols: int,
    min_countries: int,
    max_avg_latency: int,
) -> None:
    """Run all health checks."""

    print("\n🏥 ConfigStream Pipeline Health Check\n")
    print("=" * 50)

    try:
        # Check 1: Required files exist
        print("\n📁 Checking required files...")
        proxies_file = output_dir / "proxies.json"
        metadata_file = output_dir / "metadata.json"

        check_file_exists(proxies_file, "proxies.json")
        check_file_exists(metadata_file, "metadata.json")

        # Load data
        proxies = json.loads(proxies_file.read_text())
        metadata = json.loads(metadata_file.read_text())

        # Check 2: Minimum proxy count
        print("\n📊 Checking proxy count...")
        check_minimum_proxies(proxies, min_proxies)

        # Check 3: Success rate
        print("\n✅ Checking success rate...")
        check_success_rate(metadata, min_success_rate)

        # Check 4: Data freshness
        print("\n🕐 Checking data freshness...")
        check_data_freshness(metadata, max_age_hours)

        # Check 5: Protocol diversity
        print("\n🔧 Checking protocol diversity...")
        check_protocol_diversity(proxies, min_protocols)

        # Check 6: Geographic diversity
        print("\n🌍 Checking geographic diversity...")
        check_geographic_diversity(proxies, min_countries)

        # Check 7: Average latency
        print("\n⚡ Checking average latency...")
        check_average_latency(proxies, max_avg_latency)

        # All checks passed
        print("\n" + "=" * 50)
        print("✅ All health checks passed!")
        print("=" * 50 + "\n")

    except HealthCheckError as e:
        print(f"\n{e}")
        print("\n" + "=" * 50)
        print("❌ Health check failed!")
        print("=" * 50 + "\n")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Check ConfigStream pipeline health")

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Output directory to check (default: output/)",
    )

    parser.add_argument(
        "--min-proxies",
        type=int,
        default=100,
        help="Minimum number of proxies (default: 100)",
    )

    parser.add_argument(
        "--min-success-rate",
        type=float,
        default=0.01,
        help="Minimum success rate 0-1 (default: 0.01)",
    )

    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=12,
        help="Maximum data age in hours (default: 12)",
    )

    parser.add_argument(
        "--min-protocols",
        type=int,
        default=3,
        help="Minimum number of protocols (default: 3)",
    )

    parser.add_argument(
        "--min-countries",
        type=int,
        default=5,
        help="Minimum number of countries (default: 5)",
    )

    parser.add_argument(
        "--max-avg-latency",
        type=int,
        default=5000,
        help="Maximum average latency in ms (default: 5000)",
    )

    args = parser.parse_args()

    run_health_checks(
        output_dir=args.output_dir,
        min_proxies=args.min_proxies,
        min_success_rate=args.min_success_rate,
        max_age_hours=args.max_age_hours,
        min_protocols=args.min_protocols,
        min_countries=args.min_countries,
        max_avg_latency=args.max_avg_latency,
    )


if __name__ == "__main__":
    main()
