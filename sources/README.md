# Proxy Sources

This directory contains the source lists for the ConfigStream pipeline.

## Structure
Sources are distributed across 14 batch files (`batch_*.txt`) to allow parallel
processing while keeping links from the same project spread across shards.

## Policy: One Canonical Link Per Provider
To avoid duplication and wasted bandwidth, we strictly enforce a **Canonical Link Policy**:

1.  **Universal First**: If a provider offers a "Universal" or "All" endpoint (e.g., `type=all`), use THAT link only.
2.  **No Subsets**: Do NOT add separate country-specific (e.g., `country=US`) or protocol-specific (e.g., `type=socks5`) links if the Universal link is present.
3.  **Exception**: If a provider *only* offers separated lists and no universal endpoint, you may include the necessary subsets, but ensure they don't overlap if possible.

## Adding New Sources
1.  Verify the source provides a list of proxies (Text, JSON, Base64, etc.).
2.  Check if it's already in the list (grep for the domain).
3.  Add it to `consolidated_sources.txt` or run `scripts/deduplicate_sources.py` to redistribute.

## Automated Optimization
Run `python scripts/deduplicate_sources.py` to:
1.  Deduplicate sources based on the policy.
2.  Redistribute sources across batch files for load balancing.
