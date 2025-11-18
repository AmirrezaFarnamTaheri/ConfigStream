from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, List, Any

from .models import Proxy
# Imports from new location
from .filtering import dedupe_and_shuffle

logger = logging.getLogger(__name__)


def select_chosen_proxies(
    proxies: List[Proxy], top_per_protocol: int = 40, total_limit: int = 1000
) -> List[Proxy]:
    """
    Selects a high-quality subset of proxies for the 'chosen' output.
    Prioritizes diversity (top N per protocol) then latency.
    """
    # First, deduplicate to be safe
    unique_proxies = dedupe_and_shuffle(proxies)

    # Group by protocol
    by_proto: Dict[str, List[Proxy]] = defaultdict(list)
    for p in unique_proxies:
        by_proto[p.protocol].append(p)

    # Sort each group by latency
    for proto in by_proto:
        by_proto[proto].sort(key=lambda p: p.latency or float('inf'))

    chosen: List[Proxy] = []
    seen_configs = set()

    # 1. Take top N from each protocol
    for proto, p_list in by_proto.items():
        for p in p_list[:top_per_protocol]:
            if p.config not in seen_configs:
                chosen.append(p)
                seen_configs.add(p.config)

    # 2. Fill remainder with global best
    if len(chosen) < total_limit:
        remaining_slots = total_limit - len(chosen)
        global_sorted = sorted(unique_proxies, key=lambda p: p.latency or float('inf'))

        for p in global_sorted:
            if remaining_slots <= 0:
                break
            if p.config not in seen_configs:
                chosen.append(p)
                seen_configs.add(p.config)
                remaining_slots -= 1

    return chosen


def get_selection_stats(all_proxies: List[Proxy], chosen_proxies: List[Proxy]) -> Dict[str, Any]:
    """Generate statistics about the selection process."""
    return {
        "total_pool": len(all_proxies),
        "selected_count": len(chosen_proxies),
        "selection_ratio": len(chosen_proxies) / len(all_proxies) if all_proxies else 0,
    }
