# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
from typing import List, Dict, Optional

from configstream.models import Proxy
from configstream.utils import save_json_file
from configstream.test_cache import TestResultCache

logger = logging.getLogger(__name__)


def get_country_flag(country_code: Optional[str]) -> str:
    """Convert ISO country code to flag emoji."""
    if not country_code:
        return "🌍"

    country_code = country_code.upper()
    if len(country_code) != 2:
        return "🌍"

    if country_code == "XX":
        return "🌍"

    try:
        return chr(ord(country_code[0]) + 127397) + chr(ord(country_code[1]) + 127397)
    except Exception:
        return "🌍"


def calculate_compound_score(
    proxy: Proxy,
    latency_weight: float = 1.0,
    stale_penalty: float = 2.0,
    health_cache: Optional[TestResultCache] = None,
) -> float:
    """
    Calculate a sort score (lower is better).
    If health_cache provided, incorporates reliability score (inverse).
    """
    base = proxy.latency if proxy.latency else 5000.0

    # Check 'stale' field directly (from models.py)
    if proxy.stale:
        base *= stale_penalty

    if health_cache:
        # Health score is 0.0-1.0 (higher better).
        # We want to reduce 'base' (latency-like) if health is high.
        # Sort Key = Latency / HealthScore (with a small floor to avoid div/0).
        h_score = health_cache.get_health_score(proxy)
        # Avoid zero division; clamp to a small floor.
        factor = max(h_score, 0.05)
        base = base / factor

    return base


def rank_and_rename_proxies(proxies: List[Proxy]) -> List[Proxy]:
    """
    Rank proxies by protocol and latency, renaming them like:
    VMESS-1 [🇫🇷] ||| original_name
    """
    # Sort by protocol first, then latency
    proxies.sort(key=lambda p: (p.protocol, p.latency or 9999))

    protocol_counters: Dict[str, int] = {}

    for p in proxies:
        proto = p.protocol.upper()
        count = protocol_counters.get(proto, 0) + 1
        protocol_counters[proto] = count

        # Clean remark (use plural 'remarks' from model)
        original = p.remarks or "Node"
        # Ensure max length
        if len(original) > 80:
            original = original[:77] + "..."

        # Use helper
        flag = get_country_flag(p.country_code)

        # New format: PROTO-N [FLAG] ||| Remark
        p.remarks = f"{proto}-{count} [{flag}] ||| {original}"

    return proxies


def select_top_configs(
    proxies: List[Proxy],
    total_limit: int = 1000,
    top_per_protocol: int = 50,
    output_dir: str = "output",
    save_metadata: bool = True,
    health_cache: Optional[TestResultCache] = None,
) -> List[Proxy]:
    """
    Select top proxies ensuring protocol diversity.
    Also saves metadata.json with stats.
    Includes health/reliability in selection if cache provided.
    """
    if not proxies:
        return []

    # Sort all by compound score (latency + health)
    # Using a dedicated scoring function helps readability
    proxies.sort(key=lambda x: calculate_compound_score(x, health_cache=health_cache))

    selected: List[Proxy] = []
    protocol_counts: Dict[str, int] = {}

    # 1. Take top N per protocol
    remaining = []
    for p in proxies:
        proto = p.protocol
        if protocol_counts.get(proto, 0) < top_per_protocol:
            selected.append(p)
            protocol_counts[proto] = protocol_counts.get(proto, 0) + 1
        else:
            remaining.append(p)

    # 2. Fill rest with best remaining (regardless of protocol)
    needed = total_limit - len(selected)
    if needed > 0:
        # Remaining are already sorted by quality
        selected.extend(remaining[:needed])

    # Final re-sort by latency for user display? Or keep quality sort?
    # Usually users prefer latency sort in client.
    selected.sort(key=lambda x: x.latency or 9999)

    # Generate Metadata
    if save_metadata:
        try:
            # Just basic metadata if stats object not available here
            # But usually we pass stats separately.
            # Here we just save what we can compute.
            meta = {
                "total_selected": len(selected),
                "protocols": protocol_counts,
                "countries": {},  # Would need to compute
            }
            save_json_file(meta, f"{output_dir}/metadata_selection.json")
        except Exception:
            pass  # Non-critical

    return selected
