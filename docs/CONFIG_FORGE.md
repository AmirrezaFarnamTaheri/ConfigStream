# vwarp Configuration Guide & Examples

This comprehensive guide covers the complete configuration system for vwarp, including all connection options, obfuscation settings, and ready-to-use example configurations.

## 📄 Quick Start

### 🌟 Recommended for Everyone (All Countries)
```bash
# Use the universal working configuration (recommended first choice)
vwarp --config docs/examples/sample-working.json --masque

# Copy and customize for your needs
cp docs/examples/sample-working.json my-config.json
# Edit my-config.json with your settings
vwarp --config my-config.json --masque
```

### Alternative Quick Options
```bash
# CLI presets (no config file needed)
vwarp --masque --noize-preset moderate

# Use complete template for custom setups
cp docs/examples/sample-working.json my-config.json
vwarp --config my-config.json --masque
```

## 📁 Available Example Configurations

### 🌟 `sample-working.json` (RECOMMENDED FIRST CHOICE)
- **Use case**: Universal configuration - works in all countries and network conditions
- **Performance**: Optimized balance (~15-30ms latency, ~8-15% bandwidth)
- **Features**:
  - Tested and proven configuration
  - Balanced MASQUE + WireGuard settings
  - Works in China, Iran, Russia, and other restrictive countries
  - Corporate network friendly
- **Recommended for**: 🌍 **ALL COUNTRIES - Start here first!**

### `basic-obfuscation.json`
- **Use case**: Light filtering and basic DPI detection systems
- **Performance**: Low overhead (~10-20ms latency, ~5-10% bandwidth)
- **Features**: Minimal MASQUE noize (Jc: 5-10), basic protocol mimicry
- **Recommended for**: Corporate networks, light censorship

### `moderate-obfuscation.json`
- **Use case**: Corporate firewalls and moderate DPI systems
- **Performance**: Medium overhead (~30-50ms latency, ~10-20% bandwidth)
- **Features**: Enhanced MASQUE + WireGuard obfuscation, fragmentation enabled
- **Recommended for**: Government networks, ISP-level filtering

### `heavy-obfuscation.json`
- **Use case**: Extreme censorship scenarios (fallback if sample-working fails)
- **Performance**: High overhead (~50-100ms latency, ~20-40% bandwidth)
- **Features**: Maximum obfuscation (Jc: 50+), full protocol mimicry
- **Recommended for**: Last resort for strictest networks

### Configuration Templates
Use any of the above configurations as templates for creating custom configurations. The `sample-working.json` serves as the best starting point for most use cases.

## 🔧 Complete Configuration Reference

### 1. Basic Connection Settings
```json
{
  "version": "1.0",                     // Config format version
  "bind": "127.0.0.1:8086",            // SOCKS5 proxy listen address
  "endpoint": "162.159.192.1:2408",     // Cloudflare WARP endpoint
  "key": "your-warp-license-key-here",  // Your WARP+ license key (optional)
  "dns": "1.1.1.1",                    // DNS server for name resolution
  "test_url": "https://cp.cloudflare.com/", // URL for connectivity tests
  "proxy": "socks5://127.0.0.1:1080"   // Upstream SOCKS5 proxy (optional)
}
```

### 2. WireGuard Configuration
```json
{
  "wireguard": {
    "enabled": true,                    // Enable/disable WireGuard mode
    "config": "/path/to/wg.conf",      // Path to existing WG config (optional)
    "reserved": "1,2,3",               // Reserved bytes (decimal format)
    "fwmark": 0,                       // Firewall mark for routing (Linux only)
    "atomicnoize": {
      // Signature Packets (in CPS format)
      "I1": "<b 0c0d0e0f>",           // Initial signature packet
      "I2": "<b 0xc700...>",          // Large signature packet
      "I3": "<b 040506>",             // Medium signature packet
      "I4": "<b 0708>",               // Small signature packet
      "I5": "<b 09>",                 // Minimal signature packet

      // Junk Packet Configuration
      "Jc": 85,                       // Total junk packets to send
      "Jmin": 40,                     // Minimum junk packet size (bytes)
      "Jmax": 90,                     // Maximum junk packet size (bytes)
      "JcAfterI1": 3,                 // Junk packets after I1
      "JcBeforeHS": 5,                // Junk packets before handshake
      "JcAfterHS": 4,                 // Junk packets after handshake

      // Advanced Timing
      "JunkInterval": 150000000,      // Delay between junk packets (150ms)
      "HandshakeDelay": 25000000,     // Delay before handshake (25ms)
      "AllowZeroSize": true           // Allow zero-size packets
    }
  }
}
```

### 3. MASQUE Configuration
```json
{
  "masque": {
    "enabled": true,                    // Enable/disable MASQUE mode
    "preferred": false,                 // Prefer over WireGuard when both enabled
    "config": {
      // Signature Packets (MASQUE noize format)
      "i1": "<b 0d0a0d0a>",           // HTTP-like signature
      "i2": "<b 0xc700...>",          // Large signature
      "i3": "<b 0102>",               // Simple signature
      "i4": "<b 030405>",             // Medium signature
      "i5": "<b 060708>",             // Complex signature

      // Fragmentation Settings
      "fragment_size": 512,           // Fragment size in bytes
      "fragment_initial": true,       // Fragment Initial packets
      "FragmentDelay": 5000000,       // Delay between fragments (5ms)

      // Padding Configuration
      "PaddingMin": 16,               // Minimum padding bytes
      "PaddingMax": 64,               // Maximum padding bytes
      "RandomPadding": true,          // Use random padding

      // Junk Packet Configuration
      "Jc": 15,                       // Total junk packets
      "Jmin": 30,                     // Minimum junk size
      "Jmax": 120,                    // Maximum junk size
      "JcBeforeHS": 3,                // Junk before handshake
      "JcAfterI1": 2,                 // Junk after first signature
      "JcDuringHS": 5,                // Junk during handshake

      // Protocol Mimicry
      "MimicProtocol": "https",       // Mimic protocol (https/http/quic)
      "SNIFragmentation": true,       // Fragment SNI in TLS ClientHello
      "MimicTLS": true,               // Add TLS-like headers
      "CustomHeaders": true           // Add custom HTTP headers
    }
  }
}
```

### 4. Additional Options
```json
{
  "psiphon": {
    "enabled": false,                   // Enable Psiphon integration
    "country": "US"                     // Country code for exit node
  },
  "metadata": {
    "name": "Production Config",        // Human-readable name
    "description": "Production setup with heavy obfuscation",
    "author": "admin",                  // Config author
    "created_at": "2025-01-01T00:00:00Z" // Creation timestamp
  }
}
```

## ⚙️ Configuration Comparison

| Feature | Sample-Working ⭐ | Basic | Moderate | Heavy |
|---------|------------------|-------|----------|--------|
| **MASQUE Junk Packets** | 15 | 5-10 | 15-25 | 30-50 |
| **WireGuard Junk Packets** | 25 | 10-20 | 25-50 | 50-100 |
| **Protocol Mimicry** | HTTPS | QUIC | HTTPS | HTTPS |
| **Fragmentation** | Enabled | Disabled | Basic | Full |
| **SNI Fragmentation** | Yes | No | Yes | Yes |
| **Random Padding** | Optimized | Minimal | Medium | Maximum |
| **Timing Randomization** | Balanced | Basic | Medium | Complex |
| **Memory Usage** | ~75MB | ~50MB | ~100MB | ~200MB |
| **CPU Usage** | Low-Medium | Low | Medium | High |
| **Global Compatibility** | ✅ Excellent | ⚠️ Limited | ✅ Good | ✅ Maximum |

## 🌍 Regional Recommendations

### 🌟 Universal First Choice
- **ALL COUNTRIES**: Start with `sample-working.json` - tested worldwide

### Fallback Options
- **China/Iran/Russia**: Try `heavy-obfuscation.json`
- **Corporate Networks**: Try `moderate-obfuscation.json`
- **Light Filtering**: Try `basic-obfuscation.json`
