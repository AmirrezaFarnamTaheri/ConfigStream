# vwarp Complete Obfuscation Guide

This comprehensive guide covers all obfuscation technologies available in vwarp for bypassing censorship and Deep Packet Inspection (DPI).

**🎯 Unified Configuration**: vwarp now uses a single, unified configuration file format that combines all settings (connection, obfuscation, proxy, etc.) in one place. No more scattered command-line flags!

## Overview

vwarp provides two main obfuscation technologies:
- **MASQUE Noize**: Obfuscates QUIC traffic at the MASQUE tunnel level
- **AtomicNoize**: Obfuscates WireGuard traffic directly

Both can be used together or separately depending on your censorship circumvention needs.

## MASQUE Noize Obfuscation

MASQUE Noize is a sophisticated packet obfuscation system that disguises QUIC traffic patterns to bypass DPI systems.

### Core Techniques
1. **Signature Packet Injection (I1-I5)**: Mimic legitimate protocols
2. **Junk Packet Generation**: Decoy UDP packets
3. **Protocol Mimicry**: HTTPS, DNS, or STUN
4. **Timing Obfuscation**: Controlled delays
5. **Packet Fragmentation**: Avoid signature detection
6. **Dynamic Padding**: Alter packet size patterns

### Configuration File Format
```json
{
  "masque": {
    "enabled": true,
    "config": {
      "i1": "<b 0d0a0d0a>",
      "Jc": 10,
      "Jmin": 40,
      "Jmax": 90,
      "JunkInterval": 15000000,
      "MimicProtocol": "quic"
    }
  }
}
```

## AtomicNoize Protocol

AtomicNoize is a WireGuard obfuscation protocol that makes VPN traffic appear as legitimate IPsec/IKEv2 traffic.

### Core Features
1. **IKEv2/IPsec Mimicry**
2. **Signature Packets**
3. **Junk Traffic Generation**
4. **Flexible Timing Control**

### Configuration File Format
```json
{
  "wireguard": {
    "enabled": true,
    "atomicnoize": {
      "I1": "<b 0c0d0e0f>",
      "Jc": 85,
      "JunkInterval": 150000000
    }
  }
}
```

## Usage Examples

### Light MASQUE Obfuscation
```bash
vwarp --masque --masque-noize --masque-noize-config light-config.json
```

### Heavy AtomicNoize Obfuscation
```bash
vwarp --config heavy-atomic-config.json
```
