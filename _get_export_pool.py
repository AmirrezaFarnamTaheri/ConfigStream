def _get_export_pool(proxies: List[Proxy]) -> List[Proxy]:
    """
    Selects the pool of proxies to export in subscription files.
    Prefers working proxies. If none are working, falls back to all proxies
    (excluding revived ones if they are failed) to ensure output files are not empty.
    """
    working = [p for p in proxies if p.is_working]
    if working:
        return working

    # Fallback: return all non-revived proxies (revived ones that failed are likely useless)
    return [
        p
        for p in proxies
        if not (p.protocol == "revived" or (p.details or {}).get("is_revived"))
    ]
