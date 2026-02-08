#!/usr/bin/env python3
"""ConfigStream Lab Scanner - Local Network Diagnostic & Clean IP Finder

A portable, zero-dependency Python script that helps users behind heavy
censorship discover working network paths to the free internet.

Usage:
    python lab-scanner.py                  # Full diagnostic
    python lab-scanner.py --scan-ips       # Scan for clean Cloudflare IPs only
    python lab-scanner.py --scan-dns       # Find working DNS servers
    python lab-scanner.py --scan-proxies   # Discover local/network proxies
    python lab-scanner.py --test-layers    # Test a multi-layer chain config
    python lab-scanner.py --quick          # Quick connectivity check

Designed to run on Python 3.7+ with zero external dependencies.
Works on Linux, macOS, and Windows.
"""
import argparse
import concurrent.futures
import json
import os
import platform
import socket
import ssl
import struct
import sys
import time
import urllib.request
import urllib.error
from typing import List, Tuple, Optional, Dict, Any


# ============================================================
# Constants
# ============================================================

VERSION = "1.0.0"

# Cloudflare WARP endpoints to scan
CF_IPS = [
    "162.159.192.1", "162.159.192.4", "162.159.192.5", "162.159.192.6",
    "162.159.192.8", "162.159.192.10", "162.159.192.83", "162.159.192.166",
    "162.159.192.253", "162.159.195.2", "162.159.195.3",
    "188.114.96.1", "188.114.96.101", "188.114.97.1",
    "188.114.98.224", "188.114.99.73", "188.114.99.153",
]

# Ports commonly used by Cloudflare WARP
CF_PORTS = [500, 854, 859, 864, 878, 880, 890, 891, 894, 903, 1701,
            2408, 2506, 3854, 4500, 5956, 7103, 8319]

# Well-known DNS servers to test
DNS_SERVERS = [
    ("1.1.1.1", "Cloudflare"),
    ("1.0.0.1", "Cloudflare Secondary"),
    ("8.8.8.8", "Google"),
    ("8.8.4.4", "Google Secondary"),
    ("9.9.9.9", "Quad9"),
    ("208.67.222.222", "OpenDNS"),
    ("185.228.168.9", "CleanBrowsing"),
    ("94.140.14.14", "AdGuard"),
    ("76.76.2.0", "ControlD"),
    ("77.88.8.8", "Yandex"),
]

# DoH endpoints to test
DOH_ENDPOINTS = [
    ("https://cloudflare-dns.com/dns-query", "Cloudflare DoH"),
    ("https://dns.google/dns-query", "Google DoH"),
    ("https://dns.quad9.net/dns-query", "Quad9 DoH"),
    ("https://doh.opendns.com/dns-query", "OpenDNS DoH"),
    ("https://dns.adguard-dns.com/dns-query", "AdGuard DoH"),
]

# Common local SOCKS/HTTP proxy ports to probe
PROXY_PORTS_SOCKS = [1080, 1081, 2080, 7890, 7891, 10808, 10809, 20170, 51837]
PROXY_PORTS_HTTP = [3128, 8080, 8118, 8888, 7890, 7893, 10809, 20171]

# Test URLs for connectivity verification (ordered by likelihood of being unblocked)
TEST_URLS = [
    "http://cp.cloudflare.com/generate_204",
    "http://connectivitycheck.gstatic.com/generate_204",
    "http://www.msftconnecttest.com/connecttest.txt",
    "http://captive.apple.com/hotspot-detect.html",
    "http://detectportal.firefox.com/canonical.html",
]


# ============================================================
# Utilities
# ============================================================

class Colors:
    """ANSI colors - disabled on Windows without VT support."""
    ENABLED = sys.stdout.isatty() and (os.name != "nt" or os.environ.get("WT_SESSION"))

    @staticmethod
    def _c(code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if Colors.ENABLED else text

    @staticmethod
    def green(t: str) -> str: return Colors._c("32", t)
    @staticmethod
    def red(t: str) -> str: return Colors._c("31", t)
    @staticmethod
    def yellow(t: str) -> str: return Colors._c("33", t)
    @staticmethod
    def cyan(t: str) -> str: return Colors._c("36", t)
    @staticmethod
    def bold(t: str) -> str: return Colors._c("1", t)
    @staticmethod
    def dim(t: str) -> str: return Colors._c("2", t)


def banner():
    print(Colors.bold("=" * 60))
    print(Colors.cyan("  ConfigStream Lab Scanner v" + VERSION))
    print(Colors.dim("  Find your path to the free internet"))
    print(Colors.bold("=" * 60))
    print()


def ok(msg: str):
    print(f"  {Colors.green('[OK]')}  {msg}")

def fail(msg: str):
    print(f"  {Colors.red('[--]')}  {msg}")

def info(msg: str):
    print(f"  {Colors.yellow('[**]')}  {msg}")

def section(title: str):
    print()
    print(Colors.bold(f"--- {title} ---"))
    print()


# ============================================================
# Network Probes
# ============================================================

def tcp_connect(host: str, port: int, timeout: float = 3.0) -> Tuple[bool, float]:
    """Try TCP connect and return (success, latency_ms)."""
    start = time.monotonic()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        latency = (time.monotonic() - start) * 1000
        s.close()
        return True, round(latency, 1)
    except Exception:
        return False, 0.0


def udp_probe(host: str, port: int, timeout: float = 3.0) -> Tuple[bool, float]:
    """Send a UDP probe (WireGuard handshake initiation) and check for response."""
    # WireGuard handshake initiation message (type 1, minimal)
    # This will elicit a response from a WireGuard endpoint
    probe = b"\x01\x00\x00\x00" + b"\x00" * 140
    start = time.monotonic()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout)
        s.sendto(probe, (host, port))
        try:
            data, _ = s.recvfrom(256)
            latency = (time.monotonic() - start) * 1000
            s.close()
            return len(data) > 0, round(latency, 1)
        except socket.timeout:
            s.close()
            return False, 0.0
    except Exception:
        return False, 0.0


def dns_resolve(server: str, domain: str = "cloudflare.com", timeout: float = 3.0) -> Tuple[bool, float]:
    """Send a raw DNS query to a server and check for response."""
    # Build minimal DNS query for A record
    txid = struct.pack("!H", int(time.time()) & 0xFFFF)
    flags = b"\x01\x00"  # standard query, recursion desired
    counts = b"\x00\x01\x00\x00\x00\x00\x00\x00"  # 1 question
    # Encode domain
    qname = b""
    for label in domain.split("."):
        qname += bytes([len(label)]) + label.encode()
    qname += b"\x00"
    qtype = b"\x00\x01"  # A
    qclass = b"\x00\x01"  # IN
    query = txid + flags + counts + qname + qtype + qclass

    start = time.monotonic()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout)
        s.sendto(query, (server, 53))
        data, _ = s.recvfrom(512)
        latency = (time.monotonic() - start) * 1000
        s.close()
        # Check we got at least a response with matching txid
        if len(data) > 12 and data[:2] == txid:
            ancount = struct.unpack("!H", data[6:8])[0]
            return ancount > 0, round(latency, 1)
        return False, round(latency, 1)
    except Exception:
        return False, 0.0


def http_get(url: str, timeout: float = 5.0, proxy: Optional[str] = None) -> Tuple[bool, float, int]:
    """HTTP GET request. Returns (success, latency_ms, status_code)."""
    start = time.monotonic()
    try:
        if proxy:
            handler = urllib.request.ProxyHandler({
                "http": proxy,
                "https": proxy,
            })
            opener = urllib.request.build_opener(handler)
        else:
            opener = urllib.request.build_opener()

        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        resp = opener.open(req, timeout=timeout)
        latency = (time.monotonic() - start) * 1000
        status = resp.getcode()
        resp.close()
        return True, round(latency, 1), status or 0
    except urllib.error.HTTPError as e:
        latency = (time.monotonic() - start) * 1000
        return False, round(latency, 1), e.code
    except Exception:
        return False, 0.0, 0


def tls_handshake(host: str, port: int = 443, sni: str = "", timeout: float = 5.0) -> Tuple[bool, float]:
    """Attempt a TLS handshake to check if TLS is blocked."""
    start = time.monotonic()
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        wrapped = ctx.wrap_socket(s, server_hostname=sni or host)
        wrapped.connect((host, port))
        latency = (time.monotonic() - start) * 1000
        wrapped.close()
        return True, round(latency, 1)
    except Exception:
        return False, 0.0


def socks5_handshake(host: str, port: int, timeout: float = 3.0) -> Tuple[bool, float]:
    """Try a SOCKS5 handshake to detect a SOCKS proxy."""
    start = time.monotonic()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        # SOCKS5 greeting: version=5, 1 auth method (no auth)
        s.sendall(b"\x05\x01\x00")
        resp = s.recv(2)
        latency = (time.monotonic() - start) * 1000
        s.close()
        # Valid SOCKS5 response: version=5, method=0 (no auth) or method=2 (user/pass)
        if len(resp) == 2 and resp[0] == 0x05 and resp[1] in (0x00, 0x02):
            return True, round(latency, 1)
        return False, 0.0
    except Exception:
        return False, 0.0


def http_proxy_check(host: str, port: int, timeout: float = 5.0) -> Tuple[bool, float]:
    """Check if host:port is an HTTP proxy by sending a CONNECT."""
    start = time.monotonic()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.sendall(b"CONNECT cloudflare.com:443 HTTP/1.1\r\nHost: cloudflare.com\r\n\r\n")
        resp = s.recv(128)
        latency = (time.monotonic() - start) * 1000
        s.close()
        text = resp.decode(errors="ignore")
        if "200" in text or "HTTP/" in text:
            return True, round(latency, 1)
        return False, 0.0
    except Exception:
        return False, 0.0


# ============================================================
# Scan Functions
# ============================================================

def scan_basic_connectivity() -> Dict[str, Any]:
    """Phase 1: Check what the user can access at all."""
    section("Phase 1: Basic Connectivity Diagnosis")
    results: Dict[str, Any] = {"internet": False, "dns": False, "tls": False, "cf": False}

    # 1. Raw TCP to well-known IPs
    info("Testing raw TCP connectivity...")
    targets = [("1.1.1.1", 80), ("8.8.8.8", 53), ("9.9.9.9", 443)]
    for host, port in targets:
        success, lat = tcp_connect(host, port)
        if success:
            ok(f"TCP {host}:{port} reachable ({lat}ms)")
            results["internet"] = True
        else:
            fail(f"TCP {host}:{port} unreachable")

    # 2. DNS resolution
    info("Testing DNS resolution...")
    for server, name in DNS_SERVERS[:4]:
        success, lat = dns_resolve(server)
        if success:
            ok(f"DNS {server} ({name}) works ({lat}ms)")
            results["dns"] = True
            break
        else:
            fail(f"DNS {server} ({name}) blocked/unreachable")

    # 3. TLS handshake
    info("Testing TLS connectivity...")
    tls_targets = [("cloudflare.com", 443), ("google.com", 443), ("microsoft.com", 443)]
    for host, port in tls_targets:
        success, lat = tls_handshake(host, port)
        if success:
            ok(f"TLS handshake to {host}:{port} succeeded ({lat}ms)")
            results["tls"] = True
            break
        else:
            fail(f"TLS handshake to {host}:{port} failed")

    # 4. Cloudflare accessibility
    info("Testing Cloudflare accessibility...")
    success, lat, status = http_get("http://cp.cloudflare.com/generate_204")
    if success and status in (200, 204):
        ok(f"Cloudflare reachable ({lat}ms)")
        results["cf"] = True
    else:
        fail("Cloudflare HTTP check failed")

    # Summary
    section("Diagnosis Summary")
    if results["cf"]:
        ok("You have good internet access. WARP chains should work directly.")
    elif results["tls"]:
        info("TLS works but Cloudflare may be filtered. Try TLS Fragment or CDN Worker strategy.")
    elif results["internet"]:
        info("Basic TCP works but TLS is blocked. You need a SOCKS/HTTP proxy as Layer 1.")
    elif results["dns"]:
        info("Only DNS works. Very restrictive. Try DNS tunneling or find a local proxy.")
    else:
        info("No direct internet detected. Scan for local proxies (Phase 2).")

    return results


def scan_local_proxies() -> List[Dict[str, Any]]:
    """Phase 2: Scan for local SOCKS/HTTP proxies on common ports."""
    section("Phase 2: Local Proxy Discovery")
    found: List[Dict[str, Any]] = []

    info("Scanning localhost for SOCKS5 proxies...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        futures = {}
        for port in PROXY_PORTS_SOCKS:
            futures[pool.submit(socks5_handshake, "127.0.0.1", port)] = ("socks5", port)
        for port in PROXY_PORTS_HTTP:
            futures[pool.submit(http_proxy_check, "127.0.0.1", port)] = ("http", port)

        for future in concurrent.futures.as_completed(futures):
            proto, port = futures[future]
            success, lat = future.result()
            if success:
                ok(f"Found {proto.upper()} proxy at 127.0.0.1:{port} ({lat}ms)")
                found.append({"type": proto, "host": "127.0.0.1", "port": port, "latency": lat})
            else:
                pass  # Don't spam failures for local scan

    # Also check common LAN gateway addresses
    info("Scanning LAN gateway for proxies...")
    gateways = ["192.168.1.1", "192.168.0.1", "10.0.0.1", "172.16.0.1"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futures = {}
        for gw in gateways:
            for port in [3128, 8080, 1080]:
                futures[pool.submit(tcp_connect, gw, port, 2.0)] = (gw, port)

        for future in concurrent.futures.as_completed(futures):
            host, port = futures[future]
            success, lat = future.result()
            if success:
                # Verify it's actually a proxy
                s5, _ = socks5_handshake(host, port, 2.0)
                hp, _ = http_proxy_check(host, port, 2.0)
                if s5:
                    ok(f"Found SOCKS5 proxy at {host}:{port}")
                    found.append({"type": "socks5", "host": host, "port": port, "latency": lat})
                elif hp:
                    ok(f"Found HTTP proxy at {host}:{port}")
                    found.append({"type": "http", "host": host, "port": port, "latency": lat})

    if not found:
        info("No local proxies found. You may need to configure one manually.")
        info("Common setups: Psiphon (port 1080), Lantern (port 8118), V2RayN (port 10808)")
    else:
        ok(f"Found {len(found)} local proxy(ies).")

    return found


def scan_clean_ips(top_n: int = 10, max_workers: int = 30) -> List[Dict[str, Any]]:
    """Phase 3: Scan for clean Cloudflare WARP IPs."""
    section("Phase 3: Clean Cloudflare IP Scan")
    info(f"Scanning {len(CF_IPS)} IPs x {len(CF_PORTS)} ports ({len(CF_IPS) * len(CF_PORTS)} combinations)...")
    info("This may take 30-60 seconds...")
    print()

    results: List[Dict[str, Any]] = []

    def probe(ip: str, port: int) -> Optional[Dict[str, Any]]:
        # Try UDP first (WireGuard), then TCP
        success, lat = udp_probe(ip, port, timeout=3.0)
        if success:
            return {"ip": ip, "port": port, "latency": lat, "proto": "udp"}
        success, lat = tcp_connect(ip, port, timeout=3.0)
        if success:
            return {"ip": ip, "port": port, "latency": lat, "proto": "tcp"}
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {}
        for ip in CF_IPS:
            for port in CF_PORTS:
                futures[pool.submit(probe, ip, port)] = (ip, port)

        done = 0
        total = len(futures)
        for future in concurrent.futures.as_completed(futures):
            done += 1
            if done % 50 == 0:
                print(f"\r  Progress: {done}/{total}", end="", flush=True)
            result = future.result()
            if result:
                results.append(result)

    print(f"\r  Progress: {total}/{total} - Done!    ")
    print()

    # Sort by latency
    results.sort(key=lambda x: x["latency"])
    top = results[:top_n]

    if top:
        ok(f"Found {len(results)} reachable endpoints. Top {len(top)}:")
        print()
        print(f"  {'IP':<20} {'Port':<8} {'Latency':<12} {'Proto'}")
        print(f"  {'-'*20} {'-'*8} {'-'*12} {'-'*5}")
        for r in top:
            lat_str = f"{r['latency']}ms"
            print(f"  {r['ip']:<20} {r['port']:<8} {Colors.green(lat_str):<12} {r['proto']}")
    else:
        fail("No reachable Cloudflare endpoints found.")
        info("Your ISP may be blocking all Cloudflare WARP IPs.")
        info("Try using a local proxy (Phase 2) as Layer 1, then scan again through it.")

    return top


def scan_dns_servers() -> List[Dict[str, Any]]:
    """Phase 4: Find working DNS servers."""
    section("Phase 4: DNS Server Scan")
    results: List[Dict[str, Any]] = []

    info("Testing standard DNS (UDP port 53)...")
    for server, name in DNS_SERVERS:
        success, lat = dns_resolve(server)
        if success:
            ok(f"{server:>15} ({name}) - {lat}ms")
            results.append({"server": server, "name": name, "type": "udp", "latency": lat})
        else:
            fail(f"{server:>15} ({name}) - unreachable")

    print()
    info("Testing DNS-over-HTTPS (DoH)...")
    for url, name in DOH_ENDPOINTS:
        # Use a simple GET request with dns= parameter (wireformat)
        success, lat, status = http_get(url + "?dns=AAABAAABAAAAAAAAB2V4YW1wbGUDY29tAAABAAE", timeout=5.0)
        if success:
            ok(f"{name} - {lat}ms")
            results.append({"server": url, "name": name, "type": "doh", "latency": lat})
        else:
            fail(f"{name} - unreachable")

    if not results:
        info("No working DNS servers found. Your DNS is completely blocked.")
        info("Consider using DoH through a local proxy, or hardcode IP addresses.")

    return results


def test_through_proxy(proxy_type: str, proxy_host: str, proxy_port: int) -> Dict[str, Any]:
    """Test what's reachable through a given proxy."""
    section(f"Testing Through Proxy: {proxy_type}://{proxy_host}:{proxy_port}")
    result: Dict[str, Any] = {"proxy": f"{proxy_type}://{proxy_host}:{proxy_port}", "tests": {}}

    proxy_url = f"{proxy_type}://{proxy_host}:{proxy_port}"

    for url in TEST_URLS:
        success, lat, status = http_get(url, timeout=8.0, proxy=proxy_url)
        if success:
            ok(f"[via proxy] {url} - {lat}ms (HTTP {status})")
            result["tests"][url] = {"success": True, "latency": lat, "status": status}
        else:
            fail(f"[via proxy] {url} - failed")
            result["tests"][url] = {"success": False}

    working = sum(1 for t in result["tests"].values() if t.get("success"))
    if working > 0:
        ok(f"Proxy passes {working}/{len(result['tests'])} connectivity tests.")
    else:
        fail("Proxy cannot reach any test URLs.")

    return result


def generate_chain_config(layers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a sing-box chain config from a list of layers."""
    outbounds: List[Dict[str, Any]] = []
    prev_tag = None

    for i, layer in enumerate(reversed(layers)):
        tag = f"layer-{len(layers) - i}"
        outbound: Dict[str, Any] = {"tag": tag}

        if layer["type"] == "socks5":
            outbound.update({"type": "socks", "server": layer["host"], "server_port": layer["port"], "version": "5"})
        elif layer["type"] == "http":
            outbound.update({"type": "http", "server": layer["host"], "server_port": layer["port"]})
        elif layer["type"] == "warp":
            outbound.update({
                "type": "wireguard", "server": layer["ip"], "server_port": layer["port"],
                "local_address": [f"172.16.0.{i + 2}/32"],
                "private_key": "YNS+CEQE6JIQiVWcOUJd0K8FLFeCQBONJnXCdFnMRlQ=",
                "peer_public_key": "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
                "mtu": 1280
            })
        elif layer["type"] in ("vless", "vmess", "trojan", "shadowsocks"):
            outbound.update({"type": layer["type"], "server": layer["host"], "server_port": layer["port"]})
            if layer.get("uuid"):
                outbound["uuid" if layer["type"] != "trojan" else "password"] = layer["uuid"]
            if layer.get("tls"):
                outbound["tls"] = {"enabled": True, "server_name": layer.get("sni", layer["host"])}

        if prev_tag:
            outbound["detour"] = prev_tag
        prev_tag = tag
        outbounds.append(outbound)

    # The first outbound in the list is the innermost (user-facing)
    outbounds.reverse()
    primary_tag = outbounds[0]["tag"] if outbounds else "direct"

    return {
        "log": {"level": "info"},
        "inbounds": [{"type": "mixed", "tag": "mixed-in", "listen": "127.0.0.1", "listen_port": 2080}],
        "outbounds": outbounds + [{"type": "direct", "tag": "direct"}, {"type": "block", "tag": "block"}],
        "route": {"rules": [{"inbound": ["mixed-in"], "outbound": primary_tag}], "final": primary_tag}
    }


# ============================================================
# Interactive Mode
# ============================================================

def interactive_layer_builder():
    """Walk user through building a multi-layer chain interactively."""
    section("Interactive Chain Builder")
    layers: List[Dict[str, Any]] = []

    while True:
        n = len(layers) + 1
        print(f"\n  {Colors.bold(f'--- Layer {n} ---')}")
        print("  Layer types:")
        print("    1) SOCKS5 proxy (local or remote)")
        print("    2) HTTP proxy (local or remote)")
        print("    3) Cloudflare WARP (needs clean IP)")
        print("    4) VLESS proxy")
        print("    5) VMess proxy")
        print("    6) Trojan proxy")
        print("    7) Shadowsocks proxy")
        print("    d) Done building / generate config")
        print("    q) Quit")

        choice = input(f"\n  Select layer {n} type: ").strip().lower()
        if choice == "q":
            return
        if choice == "d":
            break

        layer: Dict[str, Any] = {}
        if choice == "1":
            layer["type"] = "socks5"
            layer["host"] = input("  Host [127.0.0.1]: ").strip() or "127.0.0.1"
            layer["port"] = int(input("  Port [1080]: ").strip() or "1080")
        elif choice == "2":
            layer["type"] = "http"
            layer["host"] = input("  Host [127.0.0.1]: ").strip() or "127.0.0.1"
            layer["port"] = int(input("  Port [8080]: ").strip() or "8080")
        elif choice == "3":
            layer["type"] = "warp"
            layer["ip"] = input("  Clean IP [162.159.192.1]: ").strip() or "162.159.192.1"
            layer["port"] = int(input("  Port [2408]: ").strip() or "2408")
        elif choice in ("4", "5", "6", "7"):
            type_map = {"4": "vless", "5": "vmess", "6": "trojan", "7": "shadowsocks"}
            layer["type"] = type_map[choice]
            layer["host"] = input("  Server host: ").strip()
            layer["port"] = int(input("  Server port [443]: ").strip() or "443")
            layer["uuid"] = input("  UUID/Password: ").strip()
            use_tls = input("  TLS? [Y/n]: ").strip().lower()
            layer["tls"] = use_tls != "n"
            if layer["tls"]:
                layer["sni"] = input(f"  SNI [{layer['host']}]: ").strip() or layer["host"]
        else:
            print("  Invalid choice.")
            continue

        layers.append(layer)
        ok(f"Layer {n} added: {layer['type']} @ {layer.get('host', layer.get('ip', '?'))}:{layer['port']}")

    if not layers:
        info("No layers configured.")
        return

    # Generate config
    config = generate_chain_config(layers)
    config_json = json.dumps(config, indent=2)

    section("Generated Chain Configuration")
    print(config_json)

    # Save
    save = input("\n  Save to file? [Y/n]: ").strip().lower()
    if save != "n":
        filename = input("  Filename [chain-config.json]: ").strip() or "chain-config.json"
        with open(filename, "w") as f:
            f.write(config_json)
        ok(f"Saved to {filename}")
        print(f"\n  To run: sing-box run -c {filename}")
        print(f"  Then set your proxy to: socks5://127.0.0.1:2080")


# ============================================================
# Main
# ============================================================

def full_diagnostic():
    """Run the complete diagnostic suite."""
    connectivity = scan_basic_connectivity()
    proxies = scan_local_proxies()
    clean_ips = scan_clean_ips()
    dns = scan_dns_servers()

    # Save results
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "connectivity": connectivity,
        "local_proxies": proxies,
        "clean_ips": clean_ips,
        "dns_servers": dns,
    }

    report_file = "lab-scan-results.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    section("Scan Complete")
    ok(f"Results saved to {report_file}")

    # Recommendations
    section("Recommendations")
    if connectivity.get("cf"):
        ok("Direct WARP chain should work. Use the Lab page to build your config.")
    elif connectivity.get("tls"):
        info("Try TLS Fragment strategy or CDN Worker relay.")
        if clean_ips:
            info(f"Best clean IP: {clean_ips[0]['ip']}:{clean_ips[0]['port']} ({clean_ips[0]['latency']}ms)")
    elif connectivity.get("internet"):
        info("TLS is blocked. You need a base proxy (Layer 1) first.")
        if proxies:
            info(f"Use local proxy: {proxies[0]['type']}://{proxies[0]['host']}:{proxies[0]['port']}")
            info("Then stack WARP on top as Layer 2.")
    else:
        info("Very restricted network. Find a local proxy first:")
        info("  - Ask your network admin for proxy settings")
        info("  - Try Psiphon, Lantern, or other circumvention tools for Layer 1")
        info("  - Then run this scanner again through that proxy")

    if clean_ips:
        print()
        info("Quick WARP chain command (copy-paste):")
        best = clean_ips[0]
        print(f"  python lab-scanner.py --build-chain --layer warp:{best['ip']}:{best['port']}")

    print()
    info("For interactive chain builder: python lab-scanner.py --interactive")


def main():
    parser = argparse.ArgumentParser(
        description="ConfigStream Lab Scanner - Find your path to free internet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python lab-scanner.py                     Full diagnostic
  python lab-scanner.py --scan-ips          Scan for clean Cloudflare IPs
  python lab-scanner.py --scan-dns          Find working DNS servers
  python lab-scanner.py --scan-proxies      Discover local SOCKS/HTTP proxies
  python lab-scanner.py --interactive       Interactive chain builder
  python lab-scanner.py --quick             Quick connectivity check
  python lab-scanner.py --test-proxy socks5://127.0.0.1:1080
        """
    )
    parser.add_argument("--scan-ips", action="store_true", help="Scan for clean Cloudflare IPs")
    parser.add_argument("--scan-dns", action="store_true", help="Find working DNS servers")
    parser.add_argument("--scan-proxies", action="store_true", help="Discover local proxies")
    parser.add_argument("--quick", action="store_true", help="Quick connectivity check")
    parser.add_argument("--interactive", action="store_true", help="Interactive chain builder")
    parser.add_argument("--test-proxy", type=str, help="Test through a proxy (e.g. socks5://127.0.0.1:1080)")
    parser.add_argument("--workers", type=int, default=30, help="Max parallel workers (default: 30)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON only")
    args = parser.parse_args()

    banner()

    if args.scan_ips:
        results = scan_clean_ips(max_workers=args.workers)
        if args.json:
            print(json.dumps(results, indent=2))
    elif args.scan_dns:
        results = scan_dns_servers()
        if args.json:
            print(json.dumps(results, indent=2))
    elif args.scan_proxies:
        results = scan_local_proxies()
        if args.json:
            print(json.dumps(results, indent=2))
    elif args.quick:
        scan_basic_connectivity()
    elif args.interactive:
        interactive_layer_builder()
    elif args.test_proxy:
        # Parse proxy URL: type://host:port
        parts = args.test_proxy.replace("://", ":").split(":")
        if len(parts) >= 3:
            test_through_proxy(parts[0], parts[1], int(parts[2]))
        else:
            print("Invalid proxy format. Use: type://host:port")
    else:
        full_diagnostic()


if __name__ == "__main__":
    main()
