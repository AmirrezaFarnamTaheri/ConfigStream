"""
Consolidated Proxy Ranking and Selection Logic.
Centralizes the logic previously scattered between merge_batches.py and output.py.
"""

from collections import defaultdict
from dataclasses import replace
from typing import List, Set
from .models import Proxy


def calculate_compound_score(proxy: Proxy) -> float:
    """
    Calculate a compound score for a proxy.
    Lower is better.
    Score = Latency * ReliabilityPenalty
    """
    latency = proxy.latency if proxy.latency is not None else 5000
    # Infer reliability from available metadata or default
    reliability_penalty = 1.0
    if hasattr(proxy, "stale") and proxy.stale:
        reliability_penalty = 1.5
    return latency * reliability_penalty


def get_country_flag(country_code: str) -> str:
    """Convert country code to flag emoji."""
    if not country_code or len(country_code) != 2 or country_code == "XX":
        return "🌍"
    try:
        # Convert to regional indicator symbols
        return "".join(chr(127397 + ord(c)) for c in country_code.upper())
    except (ValueError, TypeError):
        return "🌍"


def rank_and_rename_proxies(proxies: List[Proxy]) -> List[Proxy]:
    """
    Rank proxies by protocol based on latency and rename them.
    Format: PROTOCOL-RANK [COUNTRY_FLAG] ||| ORIGINAL_NAME
    """
    # Group proxies by protocol
    proxies_by_protocol = defaultdict(list)
    for proxy in proxies:
        proxies_by_protocol[proxy.protocol].append(proxy)

    # Sort each protocol group by latency (lower is better)
    ranked_proxies = []
    for protocol, protocol_proxies in proxies_by_protocol.items():
        # Sort by latency (None values go to end)
        protocol_proxies.sort(
            key=lambda p: (p.latency is None, p.latency if p.latency else float("inf"))
        )

        # Rename with rank
        for rank, proxy in enumerate(protocol_proxies, start=1):
            protocol_upper = protocol.upper()
            country_flag = get_country_flag(proxy.country_code)
            original_name = proxy.remarks or "Unnamed"

            # New remarks format: PROTOCOL-RANK [FLAG] ||| ORIGINAL_NAME
            new_remarks = (
                f"{protocol_upper}-{rank} [{country_flag}] ||| {original_name}"
            )

            # Truncate at 80 characters to avoid overly long names
            if len(new_remarks) > 80:
                new_remarks = new_remarks[:77] + "..."

            # Create updated proxy with new remarks
            # Using model_copy(update=...) for Pydantic model
            updated_proxy = proxy.model_copy(update={"remarks": new_remarks})
            ranked_proxies.append(updated_proxy)

    return ranked_proxies


def select_top_configs(
    ranked_proxies: List[Proxy], top_per_protocol: int = 50, total_limit: int = 1000
) -> List[Proxy]:
    """
    Select top configs: top N per protocol, then fill to total_limit from overall ranking.

    Args:
        ranked_proxies: List of ranked proxies
        top_per_protocol: Number of top configs to take from each protocol (default: 50)
        total_limit: Total number of configs to select (default: 1000)

    Returns:
        List of selected proxies
    """
    # Group by protocol
    proxies_by_protocol = defaultdict(list)
    for proxy in ranked_proxies:
        proxies_by_protocol[proxy.protocol].append(proxy)

    # Ensure sorting by latency for selection
    for proto_list in proxies_by_protocol.values():
        proto_list.sort(
            key=lambda p: (p.latency is None, p.latency if p.latency else float("inf"))
        )

    # Select top N from each protocol
    selected = []
    selected_configs: Set[str] = set()  # Track selected configs to avoid duplicates

    for protocol, protocol_proxies in proxies_by_protocol.items():
        # Take top N from this protocol
        top_n = protocol_proxies[:top_per_protocol]
        for proxy in top_n:
            if proxy.config not in selected_configs:
                selected.append(proxy)
                selected_configs.add(proxy.config)

    # If we haven't reached the limit, fill from overall ranking
    if len(selected) < total_limit:
        # Sort all proxies by latency overall
        overall_ranked = sorted(
            ranked_proxies,
            key=lambda p: (p.latency is None, p.latency if p.latency else float("inf")),
        )

        # Fill the gap
        for proxy in overall_ranked:
            if len(selected) >= total_limit:
                break
            if proxy.config not in selected_configs:
                selected.append(proxy)
                selected_configs.add(proxy.config)

    return selected
