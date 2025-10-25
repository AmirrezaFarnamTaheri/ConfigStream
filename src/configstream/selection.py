"""
Proxy selection logic for generating the "chosen" subset.

Implements the selection algorithm:
- Top 40 proxies per protocol (sorted by latency)
- Fill remaining slots to reach 1000 total from all tested proxies
- Ensures diversity across protocols while prioritizing quality
"""

from typing import List, Dict
from collections import defaultdict

from .models import Proxy
from .constants import CHOSEN_TOP_PER_PROTOCOL, CHOSEN_TOTAL_TARGET


def select_chosen_proxies(all_proxies: List[Proxy]) -> List[Proxy]:
    """
    Select the "chosen" subset of proxies based on quality and diversity.

    Algorithm:
    1. Group proxies by protocol
    2. Take top N (default: 40) per protocol, sorted by latency
    3. If total < 1000, fill from remaining proxies (best latency overall)
    4. Ensure only working proxies with no security issues are selected

    Args:
        all_proxies: List of all tested proxies

    Returns:
        List of chosen proxies (up to CHOSEN_TOTAL_TARGET)
    """
    # Filter to only working proxies without security issues
    working = [
        p for p in all_proxies
        if p.is_working and not p.security_issues and p.latency is not None
    ]

    if not working:
        return []

    # Sort all proxies by latency (best first)
    working_sorted = sorted(working, key=lambda p: p.latency or float('inf'))

    # Group by protocol
    by_protocol: Dict[str, List[Proxy]] = defaultdict(list)
    for proxy in working_sorted:
        protocol = proxy.protocol.lower()
        by_protocol[protocol].append(proxy)

    chosen = []
    chosen_ids = set()

    # Step 1: Take top N per protocol
    for protocol, proxies in sorted(by_protocol.items()):
        # Already sorted by latency globally, so just take first N for this protocol
        protocol_top = proxies[:CHOSEN_TOP_PER_PROTOCOL]
        for p in protocol_top:
            if p.id not in chosen_ids:
                chosen.append(p)
                chosen_ids.add(p.id)

    # Step 2: Fill remaining slots from all remaining proxies
    if len(chosen) < CHOSEN_TOTAL_TARGET:
        remaining_needed = CHOSEN_TOTAL_TARGET - len(chosen)
        for proxy in working_sorted:
            if len(chosen) >= CHOSEN_TOTAL_TARGET:
                break
            if proxy.id not in chosen_ids:
                chosen.append(proxy)
                chosen_ids.add(proxy.id)
                remaining_needed -= 1

    # Re-sort final list by latency for clean output
    chosen.sort(key=lambda p: p.latency or float('inf'))

    return chosen[:CHOSEN_TOTAL_TARGET]


def get_selection_stats(all_proxies: List[Proxy], chosen: List[Proxy]) -> Dict[str, any]:
    """
    Generate statistics about the selection process.

    Returns dict with:
    - total_tested: Total proxies tested
    - working: Total working proxies
    - chosen_count: Number selected
    - by_protocol: Breakdown of chosen by protocol
    - coverage: Percentage of protocols represented
    """
    by_protocol_chosen: Dict[str, int] = defaultdict(int)
    for proxy in chosen:
        protocol = proxy.protocol.lower()
        by_protocol_chosen[protocol] += 1

    by_protocol_total: Dict[str, int] = defaultdict(int)
    working_count = 0
    for proxy in all_proxies:
        if proxy.is_working and not proxy.security_issues:
            working_count += 1
        protocol = proxy.protocol.lower()
        by_protocol_total[protocol] += 1

    return {
        "total_tested": len(all_proxies),
        "working": working_count,
        "chosen_count": len(chosen),
        "by_protocol_chosen": dict(by_protocol_chosen),
        "by_protocol_total": dict(by_protocol_total),
        "protocols_represented": len(by_protocol_chosen),
        "avg_latency_ms": sum(p.latency or 0 for p in chosen) / len(chosen) if chosen else 0,
        "max_latency_ms": max((p.latency or 0 for p in chosen), default=0),
    }
