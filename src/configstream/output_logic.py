    # Compute total_revived from exact counts (no heuristics)
    # Use PipelineStats.total_revived property if available, otherwise calculate
    if isinstance(stats, dict):
        total_revived_count = stats.get("total_revived", revived_warp + revived_vwarp)
    else:
        if hasattr(stats, "total_revived"):
            total_revived_count = stats.total_revived
        else:
            total_revived_count = revived_warp + revived_vwarp
