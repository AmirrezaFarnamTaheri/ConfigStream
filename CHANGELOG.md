
## [2.3.0] - 2026-02-05

### Time-Series Analytics & Evasion Metrics

**Analytics Enhancements**
- **Time-Series Charts**: Added comprehensive evasion metrics tracking over 7-day rolling window
  - Shielded (Gold) proxies count over time
  - Revived (WARP/VWARP) proxies count over time
  - uTLS enabled proxies count over time
  - DNS-Hardened proxies count over time
  - Visualized in both statistics and analytics pages
- **Evasion Trend Export**: Automatic export of evasion metrics to `data/evasion_trend.json` on each pipeline run
- **Historical Tracking**: Rolling window maintains last 7 days of evasion metrics for trend analysis

**Documentation Updates**
- Updated `docs/EVASION_IMPLEMENTATION.md` with time-series charts implementation details
- Merged `docs/COMPLETE_FEATURE_COVERAGE.md` into `docs/OUTPUT_VARIATIONS.md` (redundancy cleanup)
- Marked `docs/SMART_CHAINS_ENHANCEMENT.md` as historical reference document
- Updated `docs/ARCHITECTURE.md` with metrics and analytics section
- Updated `README.md` with analytics and monitoring section
- Removed temporary `IMPLEMENTATION_SUMMARY.md` (information merged into core docs)

**Files Modified**
- `src/configstream/history/export.py` - Added `export_evasion_trend()` function
- `src/configstream/history/tracker.py` - Added `export_evasion_trend()` method
- `src/configstream/pipeline_core/output_handler.py` - Integrated evasion trend export
- `frontend/assets/js/statistics.js` - Added evasion trend chart rendering
- `frontend/assets/js/analytics.js` - Added evasion trend chart rendering
- `frontend/analytics.html` - Added evasion trend chart container

## [2.2.0] - 2026-02-01

### Load Balancing & Vwarp Activation

**Infrastructure Improvements**
- **Load Balancing**: Redistributed sources from heavy batches (6, 10, 11, 12) into a new `batch_15` and lighter existing batches (3, 4, 5, 13) to reduce pipeline runtime.
- **Pipeline Optimization**: Enabled `FORCE_SCANNER` and `ALLOW_ACTIVE_SCANNING` in CI pipeline to activate Vwarp binary usage.
- **Vwarp Fix**: Resolved issue where vwarp binary was not being utilized, ensuring "chains" and "revived" proxies are now correctly generated.
