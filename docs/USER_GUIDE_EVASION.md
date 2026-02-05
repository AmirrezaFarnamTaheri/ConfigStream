# Evasion Mode Selection Guide

This guide helps users understand and select the appropriate evasion mode for their censorship environment.

## Understanding Evasion Modes

ConfigStream provides three evasion modes to balance between compatibility and censorship resistance:

### 1. Standard Mode

**Best for**: Normal network conditions, maximum compatibility

- **Features**: No special evasion techniques
- **Use when**: 
  - Your network is not heavily censored
  - You need maximum compatibility with all servers
  - You're experiencing connection issues with evasion features
- **Trade-off**: Lower censorship resistance, higher compatibility

### 2. Stealth Mode

**Best for**: Moderate censorship, balanced approach

- **Features**: 
  - TLS fingerprint rotation (uTLS - mimics browser)
  - TLS fragmentation (DPI shredder)
- **Use when**:
  - You experience occasional blocking
  - You need better compatibility than aggressive mode
  - You want basic DPI evasion
- **Trade-off**: Moderate censorship resistance, good compatibility

### 3. Aggressive Mode (Default)

**Best for**: Heavy censorship, maximum evasion

- **Features**: 
  - TLS fingerprint rotation (uTLS)
  - ALPN rotation
  - TLS fragmentation
  - Multiplexing with padding
- **Use when**:
  - You're in a heavily censored environment
  - Standard connections are frequently blocked
  - You need maximum evasion capabilities
- **Trade-off**: Highest censorship resistance, may have compatibility issues with some servers

## How to Select Evasion Mode

### Via Frontend UI

1. Navigate to the downloads section
2. Find the "Evasion mode" dropdown
3. Select your preferred mode:
   - **Standard** - No evasion
   - **Stealth** - Basic evasion (TLS frag + uTLS)
   - **Aggressive** - All evasion features

### Via Environment Variable

Set the `EVASION_MODE` environment variable:

```bash
# Standard mode
export EVASION_MODE=standard

# Stealth mode
export EVASION_MODE=stealth

# Aggressive mode (default)
export EVASION_MODE=aggressive
```

### Via Configuration File

Add to your `.env` file:

```env
EVASION_MODE=stealth
```

## DNS Profile Selection

Evasion modes work alongside DNS profiles:

### Standard DNS Profile
- Uses hostnames as provided
- Standard DNS resolution
- Works with all evasion modes

### DNS-Safe Profile
- Pre-resolves all hostnames to IPs
- Bypasses DNS poisoning
- Works with all evasion modes

### DNS-Hardened Profile
- Prefers IPs when available
- Embeds DoH/DoT/DoQ resolvers
- Maximum DNS censorship resistance
- Works with all evasion modes

## Recommended Combinations

### Light Censorship
- **Evasion Mode**: Standard
- **DNS Profile**: Standard
- **Use case**: Normal network, occasional blocks

### Moderate Censorship
- **Evasion Mode**: Stealth
- **DNS Profile**: DNS-Safe
- **Use case**: DNS poisoning, basic DPI

### Heavy Censorship
- **Evasion Mode**: Aggressive
- **DNS Profile**: DNS-Hardened
- **Use case**: Severe blocking, DNS poisoning, DPI

### Maximum Resistance
- **Evasion Mode**: Aggressive
- **DNS Profile**: DNS-Hardened
- **Output**: `singbox-chains.json` (includes Gold/Shielded chains)
- **Use case**: Extreme censorship, ISP-level blocking

## Troubleshooting

### Connection Failures with Aggressive Mode

If you experience connection failures with aggressive mode:

1. **Try Stealth Mode**: Some servers may not support multiplexing or ALPN rotation
2. **Check Server Compatibility**: Contact your proxy provider about evasion feature support
3. **Use Standard Mode**: Fall back to standard mode if evasion causes issues

### False Negatives in Testing

The tester now uses evasion profiles by default to avoid false negatives. If a proxy works with evasion features, it will be correctly identified as working.

### Performance Impact

- **Standard**: No performance impact
- **Stealth**: Minimal overhead (~5-10ms)
- **Aggressive**: Slight overhead (~10-20ms) due to multiplexing and fragmentation

## Technical Details

### TLS Fingerprint Rotation (uTLS)

Mimics browser TLS handshakes:
- Chrome fingerprint (default)
- Firefox, Safari, iOS (rotated deterministically)
- Bypasses "Unknown Protocol" blocks

### TLS Fragmentation

Splits TLS handshake packets:
- Fragment size: 100-200 bytes
- Sleep between fragments: 0-10ms
- Bypasses stateless DPI

### Multiplexing with Padding

HTTP/2 multiplexing with random padding:
- Protocol: h2mux
- Hides packet size patterns
- Makes traffic look like standard HTTP/2

### ALPN Rotation

Varies Application-Layer Protocol Negotiation:
- Protocols: h2, http/1.1
- Rotated deterministically per proxy
- Prevents protocol fingerprinting

## Monitoring & Analytics

ConfigStream provides comprehensive analytics to help you understand evasion effectiveness:

### Time-Series Charts
- View evasion metrics over the last 7 days
- Track shielded (Gold) proxy counts
- Monitor revived proxy success rates
- Analyze evasion feature adoption

### Accessing Analytics
1. Visit the **Analytics** page in the frontend
2. Scroll to the **Evasion Metrics Over Time** chart
3. View trends for:
   - Shielded (Gold) connections
   - Revived (WARP/VWARP) connections
   - uTLS enabled proxies
   - DNS-Hardened proxies

### Interpreting Results
- **Increasing trends**: Evasion features are working effectively
- **Stable trends**: Consistent evasion performance
- **Decreasing trends**: May indicate increased censorship or need for mode adjustment

## Best Practices

1. **Start with Standard**: Test with standard mode first
2. **Escalate Gradually**: Move to Stealth, then Aggressive if needed
3. **Monitor Performance**: Track latency and success rates
4. **Use Gold Chains**: For extreme censorship, use `singbox-chains.json` with Gold/Shielded proxies
5. **Combine with DNS Hardening**: Use DNS-hardened profiles in censored environments

## Support

For issues or questions:
- Check `docs/CENSORSHIP_EVASION.md` for technical details
- Review `docs/EVASION_IMPLEMENTATION.md` for implementation notes
- Check analytics dashboard for evasion success rates

