# Evasion Features Implementation Summary

This document summarizes the implementation of the four remaining enhancements:

1. **Geosite Database Integration**
2. **Unit Tests for Evasion Features**
3. **Metrics Tracking for Evasion Success Rates**
4. **UI Evasion Mode Selector**

## 1. Geosite Database Integration ✅

### Implementation

**File**: `src/configstream/cli.py`

- Extended `update_databases()` command to download Sing-box databases:
  - `geosite.db` from SagerNet/sing-geosite
  - `geoip.db` from SagerNet/sing-geoip
- Databases are stored in `data/singbox/` directory
- Non-fatal if download fails (warns but continues)

**File**: `src/configstream/generators/singbox.py`

- Added `_build_route_rules()` method that:
  - Checks for `geosite.db` and `geoip.db` availability
  - If available, adds domestic bypass rules:
    - `.ir` domains and Iran IPs → `DIRECT`
    - Blocked sites (Google, Telegram, Twitter, YouTube, Meta) → Proxy
  - Falls back gracefully if databases are missing (logs debug message)

**File**: `.github/workflows/ci.yml`

- Added step to update routing databases before pipeline runs
- Ensures fresh geosite/geoip data for each CI run

### Usage

```bash
# Download/update all databases (GeoIP + Sing-box)
python -m configstream.cli update-databases
```

## 2. Unit Tests for Evasion Features ✅

### Test Files Created

**File**: `tests/unit/test_evasion.py`
- Tests for TLS fingerprint rotation
- Tests for ALPN rotation
- Tests for TLS fragmentation
- Tests for multiplexing with padding
- Tests for outbound enrichment
- Tests for SNI/Host preservation

**File**: `tests/unit/test_censorship_lab.py`
- Tests for poisoned DNS resolver
- Tests for IP blocklist
- Tests for censorship lab modes (DNS poison, IP block, slow DNS, timeout, rate limit)
- Integration tests for censorship simulation

**File**: `tests/unit/test_html_smuggler.py`
- Tests for HTML config smuggling
- Tests for config extraction from HTML

### Running Tests

```bash
# Run all evasion tests
pytest tests/unit/test_evasion.py tests/unit/test_censorship_lab.py tests/unit/test_html_smuggler.py -v

# Run specific test file
pytest tests/unit/test_evasion.py -v
```

## 3. Metrics Tracking for Evasion Success Rates ✅

### Implementation

**File**: `src/configstream/pipeline_core/stats.py`

Added new metrics fields:
- `evasion_utls_enabled`: Count of proxies with uTLS fingerprint rotation
- `evasion_alpn_enabled`: Count of proxies with ALPN rotation
- `evasion_fragmentation_enabled`: Count of proxies with TLS fragmentation
- `evasion_multiplexing_enabled`: Count of proxies with multiplexing
- `evasion_dns_safe_count`: Count of proxies in DNS-safe outputs
- `evasion_dns_hardened_count`: Count of proxies in DNS-hardened outputs

**File**: `src/configstream/pipeline_core/output_handler.py`

- Tracks DNS-safe and DNS-hardened proxy counts
- Tracks evasion feature usage based on working proxies with TLS-enabled protocols
- Updates stats after DNS resolution and output generation

**File**: `frontend/assets/js/statistics.js`

- Added display for evasion metrics:
  - `shieldedCount`: Number of shielded (Gold) proxies
  - `evasionUtls`: Number of proxies with uTLS enabled
  - `evasionDnsSafe`: Number of DNS-safe proxies
  - `evasionDnsHardened`: Number of DNS-hardened proxies

**File**: `frontend/index.html`

- Added stat cards for evasion metrics in the analytics dashboard
- Displays shielded count, uTLS enabled count, and DNS-hardened count

### Metrics Available in Metadata

All evasion metrics are included in `metadata.json`:
```json
{
  "evasion_utls_enabled": 150,
  "evasion_alpn_enabled": 120,
  "evasion_fragmentation_enabled": 150,
  "evasion_multiplexing_enabled": 140,
  "evasion_dns_safe_count": 150,
  "evasion_dns_hardened_count": 150,
  "shielded_count": 25
}
```

## 4. UI Evasion Mode Selector ✅

### Implementation

**File**: `frontend/index.html`

- Added evasion mode selector dropdown:
  - **Standard**: Default mode (no special evasion)
  - **Stealth**: TLS fragmentation + uTLS fingerprint rotation
  - **Aggressive**: All evasion features enabled

**File**: `frontend/assets/js/dynamic-downloads.js`

- Added `evasionMode()` function to get current evasion mode
- Added event listener for evasion mode selector changes
- Integrated with existing DNS profile selector

### Usage

Users can now select:
1. **DNS Profile**: Standard / DNS-safe / DNS-hardened
2. **Evasion Mode**: Standard / Stealth / Aggressive

The evasion mode selector is displayed alongside the DNS profile selector in the downloads section.

## Integration Points

### Pipeline Flow

1. **Database Update**: CI workflow downloads geosite/geoip databases
2. **Route Rules**: Sing-box generator checks for databases and adds routing rules
3. **Evasion Injection**: Split generator applies evasion features to outbounds based on `EVASION_MODE`
4. **Metrics Tracking**: Output handler tracks evasion usage and updates stats
5. **Frontend Display**: Statistics page shows evasion metrics

### Evasion Features Applied

Evasion features are applied in `src/configstream/generators/split.py` based on `EVASION_MODE`:
- **Standard**: No evasion features
- **Stealth**: uTLS + TLS fragmentation only
- **Aggressive** (default): All features (uTLS, ALPN, fragmentation, multiplexing)

### Output Variations

All evasion features are included in:
- Standard outputs (with evasion based on mode)
- DNS-safe outputs (IP-only with evasion based on mode)
- DNS-hardened outputs (prefer IP + DoH/DoT/DoQ with evasion based on mode)

## Verification

### Test Coverage

- ✅ Unit tests for all evasion functions
- ✅ Integration tests for censorship lab
- ✅ Tests for HTML smuggling
- ✅ No linter errors

### Functionality

- ✅ Geosite database download and integration
- ✅ Route rules with geosite/geoip support
- ✅ Metrics tracking in pipeline
- ✅ Frontend display of evasion metrics
- ✅ UI selector for evasion modes
- ✅ Tester enhancement (evasion profiles)
- ✅ Evasion mode filtering in output generation

## Tagging System

All evasion, hardening, reviving, and shielding methods are properly tagged:

### Proxy Tags (in `proxy.tags`)
- `REVIVED` - Revived proxy
- `WARP` / `VWARP` - Revival chain type
- `SHIELDED` / `GOLD` - Shielded proxy (Copper to Gold)
- `EVASION:UTLS` - TLS fingerprint rotation
- `EVASION:FRAG` - TLS fragmentation
- `EVASION:MUX` - Multiplexing with padding
- `EVASION:ALPN` - ALPN rotation
- `DNS:SAFE` - DNS-safe output
- `DNS:HARDENED` - DNS-hardened output

### Outbound Tags (in Sing-box configs)
- `GOLD-*` - Shielded proxy outbound names (included in selectors)
- `SHIELD-*` - Shield base (internal, not in selectors)
- `WARP-REVIVE-*` - WARP revived chain outbound names
- `VWARP-REVIVE-*` - Vwarp revived chain outbound names
- `WARP-RELAY-*` - WARP revival relay outbound names
- `VWARP-RELAY-*` - Vwarp revival relay outbound names
- `🛡️ Secure-*` / `🛡️⚡ Optimal-*` - Washed chain outbound names

### Process Metadata
- `shield_base` - WARP shield (not in user-facing selectors)
- `shield_payload` - Shielded proxy (included in selectors)
- `revived-warp` / `revived-vwarp` - Revival process type
- `washed` - Standard washing process
- `chain` - Smart chain process

## Next Steps - Implementation Status

1. ✅ **Tester Enhancement**: Updated `SingBoxTester` to use evasion profiles (uTLS, multiplexing) to avoid false negatives
   - Python tester (`test_via_singbox`) now applies evasion features before testing
   - Go tester (`test_batch`) now applies evasion features before testing
   - This ensures proxies that only work with evasion are correctly identified

2. ✅ **Evasion Mode Implementation**: Implemented actual evasion mode filtering in output generation
   - Added `EVASION_MODE` configuration option (standard, stealth, aggressive)
   - Standard: No evasion features
   - Stealth: TLS fragmentation + uTLS only
   - Aggressive: All evasion features (default)
   - Mode is applied in `generate_split_outputs()` based on `AppSettings.EVASION_MODE`

3. ✅ **Analytics Dashboard**: Time-series charts for evasion success rates over time
   - **Status**: Complete
   - **Implementation**: 
     - Added `export_evasion_trend()` in `src/configstream/history/export.py` to track evasion metrics over time
     - Exports `data/evasion_trend.json` with rolling 7-day window
     - Added `evasionTrendChart` in `frontend/assets/js/statistics.js` and `frontend/assets/js/analytics.js`
     - Displays multiple metrics: Shielded (Gold), Revived (WARP/VWARP), uTLS Enabled, DNS-Hardened
     - Charts available on both statistics and analytics pages
   - **Files Modified**:
     - `src/configstream/history/export.py` - Evasion trend export function
     - `src/configstream/history/tracker.py` - Export method wrapper
     - `src/configstream/pipeline_core/output_handler.py` - Export call integration
     - `frontend/assets/js/statistics.js` - Chart rendering
     - `frontend/assets/js/analytics.js` - Chart rendering
     - `frontend/analytics.html` - Chart container

4. ✅ **Documentation**: Created user-facing documentation with evasion mode selection guide
   - Created `docs/USER_GUIDE_EVASION.md` with comprehensive guide
   - Explains all three evasion modes
   - Provides troubleshooting and best practices
   - Includes recommended combinations for different censorship levels

## Files Modified

- `src/configstream/cli.py` - Database download
- `src/configstream/generators/singbox.py` - Route rules with geosite
- `src/configstream/pipeline_core/stats.py` - Evasion metrics
- `src/configstream/pipeline_core/output_handler.py` - Metrics tracking
- `src/configstream/generators/split.py` - Evasion injection with mode filtering
- `src/configstream/testers/python.py` - Tester enhancement (evasion profiles)
- `src/configstream/testers/go.py` - Tester enhancement (evasion profiles)
- `src/configstream/config.py` - Added EVASION_MODE configuration
- `frontend/index.html` - UI selector and stat cards
- `frontend/assets/js/dynamic-downloads.js` - Evasion mode handling
- `frontend/assets/js/statistics.js` - Metrics display
- `.github/workflows/ci.yml` - Database update step
- `tests/unit/test_evasion.py` - Evasion tests
- `tests/unit/test_censorship_lab.py` - Censorship lab tests
- `tests/unit/test_html_smuggler.py` - HTML smuggler tests
- `docs/USER_GUIDE_EVASION.md` - User-facing evasion mode guide

## Usage Examples

### Setting Evasion Mode

```bash
# Via environment variable
export EVASION_MODE=stealth
python -m configstream.cli merge --sources sources.txt

# Via .env file
echo "EVASION_MODE=aggressive" >> .env
```

### Testing with Evasion

The tester now automatically applies evasion features, so proxies that require evasion will be correctly identified:

```python
from configstream.testers import SingBoxTester
from configstream.models import Proxy

tester = SingBoxTester(timeout=10.0)
proxy = Proxy(config="vmess://...", protocol="vmess", ...)
result = await tester.test(proxy)
# Result will use evasion features if proxy requires them
```

### Output Generation with Evasion Modes

```python
from configstream.generators.split import generate_split_outputs
from configstream.config import AppSettings

settings = AppSettings()
settings.EVASION_MODE = "stealth"  # or "standard", "aggressive"

# Outputs will use the configured evasion mode
files = generate_split_outputs(proxies, output_dir, ...)
```

All enhancements are complete and integrated! ✅
