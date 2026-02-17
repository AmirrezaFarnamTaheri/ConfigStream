# SOCKS5 Proxy Chaining Guide

This guide explains how to use Vwarp with SOCKS5 proxy chaining to create double-VPN configurations for enhanced privacy and censorship circumvention.

## Quick Reference

| Use Case | Command |
|----------|---------|
| Basic proxy chaining | `Vwarp --proxy socks5://127.0.0.1:1080` |
| With AtomicNoize | `Vwarp --proxy socks5://127.0.0.1:1080 --atomicnoize-enable` |
| Maximum privacy | `Vwarp --proxy socks5://127.0.0.1:1080 --atomicnoize-enable --atomicnoize-junk-size 50` |
| Through SSH tunnel | `ssh -D 1080 -N user@server` then `Vwarp --proxy socks5://127.0.0.1:1080` |
| With Psiphon | `Vwarp --cfon --country US --proxy socks5://127.0.0.1:1080` |
| Scan through proxy | `Vwarp --proxy socks5://127.0.0.1:1080 --scan --rtt 800ms` |

## Overview

SOCKS5 proxy chaining allows you to route your WireGuard/WARP traffic through another VPN or proxy server, creating a "double-VPN" configuration. This adds an extra layer of privacy and can help bypass advanced censorship systems.

### Traffic Flow

```
Your Application
       ↓
   WARP SOCKS5 Proxy (127.0.0.1:8086)
       ↓
   WireGuard (with AtomicNoize)
       ↓
   SOCKS5 Proxy (Your VPN/Proxy)
       ↓
   Internet
```

## Use Cases

### 1. Bypass Advanced Censorship
Chain WARP through a local VPN to hide WireGuard traffic patterns:
```bash
Vwarp --proxy socks5://127.0.0.1:1080 --atomicnoize-enable --bind 127.0.0.1:8086
```

### 2. Change Exit Location
Use WARP for speed while routing through a specific geographic location:
```bash
# First VPN in Japan (SOCKS5 on port 1080)
# WARP exit in US
Vwarp --proxy socks5://127.0.0.1:1080 --bind 127.0.0.1:8086
```

### 3. Corporate Network Traversal
Route WARP through corporate proxy:
```bash
Vwarp --proxy socks5://proxy.company.com:1080 --bind 127.0.0.1:8086
```

### 4. Triple-VPN with Psiphon
Combine Psiphon, WARP, and external proxy:
```bash
Vwarp --cfon --country US --proxy socks5://127.0.0.1:1080 --bind 127.0.0.1:8086
```
