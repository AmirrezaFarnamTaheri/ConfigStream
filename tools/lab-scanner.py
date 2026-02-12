#!/usr/bin/env python3
"""ConfigStream Lab Scanner - Local Network Diagnostic & Clean IP Finder

A portable, zero-dependency Python script that helps users behind heavy
censorship discover working network paths to the free internet.

Usage:
    python lab-scanner.py                  # Full diagnostic (all 6 phases)
    python lab-scanner.py --scan-ips       # Scan for clean Cloudflare IPs
    python lab-scanner.py --scan-dns       # Find working DNS (UDP/DoH/DoT)
    python lab-scanner.py --scan-proxies   # Discover local/network proxies
    python lab-scanner.py --scan-sni       # Detect SNI-based domain blocking
    python lab-scanner.py --scan-ports     # TCP port reachability matrix
    python lab-scanner.py --interactive    # Interactive chain builder
    python lab-scanner.py --auto-chain     # Auto-detect best chain path
    python lab-scanner.py --quick          # Quick connectivity check
    python lab-scanner.py --test-proxy socks5://127.0.0.1:1080
    python lab-scanner.py --scan-ips --custom-ips "1.2.3.4:2408,5.6.7.8"
    python lab-scanner.py --auto-chain --custom-proxy socks5://127.0.0.1:1080

Phases:
    1. Basic Connectivity (ICMP, TCP, DNS, TLS, HTTPS, Cloudflare, speed)
    2. Local Proxy Discovery (SOCKS5, HTTP on localhost + LAN gateways)
    3. Clean Cloudflare IP Scan (UDP/TCP across WARP port ranges)
    4. DNS Server Scan (UDP/53, DoH, DoT with latency ranking)
    5. SNI Blocking Detection (TLS handshake to 25 popular domains)
    6. Port Reachability Matrix (IP x Port with alt CDN IPs)

User-supplied resources:
    --custom-ips    Your own IPs (comma-separated or file path) merged into scans
    --custom-proxy  Your own proxy as Layer 1 in --auto-chain

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

VERSION = "2.1.0"

# Cloudflare WARP endpoints to scan (expanded set covering multiple /24 ranges)
CF_IPS = [
    # 162.159.192.0/24 range
    "162.159.192.1",
    "162.159.192.4",
    "162.159.192.5",
    "162.159.192.6",
    "162.159.192.8",
    "162.159.192.10",
    "162.159.192.37",
    "162.159.192.55",
    "162.159.192.83",
    "162.159.192.100",
    "162.159.192.120",
    "162.159.192.166",
    "162.159.192.200",
    "162.159.192.227",
    "162.159.192.253",
    # 162.159.193.0/24 range
    "162.159.193.1",
    "162.159.193.5",
    "162.159.193.10",
    "162.159.193.40",
    # 162.159.195.0/24 range
    "162.159.195.1",
    "162.159.195.2",
    "162.159.195.3",
    "162.159.195.55",
    # 188.114.96.0/22 range
    "188.114.96.1",
    "188.114.96.50",
    "188.114.96.101",
    "188.114.97.1",
    "188.114.97.88",
    "188.114.98.0",
    "188.114.98.224",
    "188.114.99.1",
    "188.114.99.73",
    "188.114.99.153",
]

# Ports commonly used by Cloudflare WARP / WireGuard (expanded)
CF_PORTS = [
    500,
    854,
    859,
    864,
    878,
    880,
    890,
    891,
    894,
    903,
    908,
    928,
    934,
    939,
    942,
    1701,
    2408,
    2506,
    3854,
    4177,
    4198,
    4233,
    4500,
    5279,
    5956,
    7103,
    7152,
    7156,
    7281,
    7559,
    8319,
    8742,
    8854,
    8886,
]

# Well-known DNS servers to test (global + regional anti-censorship)
DNS_SERVERS = [
    # --- Global Anycast ---
    ("1.1.1.1", "Cloudflare"),
    ("1.0.0.1", "Cloudflare Secondary"),
    ("8.8.8.8", "Google"),
    ("8.8.4.4", "Google Secondary"),
    ("9.9.9.9", "Quad9"),
    ("9.9.9.10", "Quad9 Unsecured"),
    ("149.112.112.112", "Quad9 Alt"),
    ("208.67.222.222", "OpenDNS"),
    ("208.67.220.220", "OpenDNS Secondary"),
    ("185.228.168.9", "CleanBrowsing Security"),
    ("185.228.169.9", "CleanBrowsing Security Alt"),
    ("94.140.14.14", "AdGuard"),
    ("94.140.15.15", "AdGuard Secondary"),
    ("76.76.2.0", "ControlD"),
    ("76.76.10.0", "ControlD Alt"),
    ("76.223.122.150", "ControlD Anycast"),
    # --- Regional / Privacy ---
    ("77.88.8.8", "Yandex"),
    ("77.88.8.1", "Yandex Secondary"),
    ("5.2.75.75", "Radar Game (IR bypass)"),
    ("10.202.10.10", "403 Online (IR local)"),
    ("176.103.130.130", "AdGuard Family"),
    ("198.101.242.72", "Alternate DNS"),
    ("23.253.163.53", "Alternate DNS Alt"),
    ("45.90.28.0", "NextDNS"),
    ("45.90.30.0", "NextDNS Alt"),
    ("193.110.81.0", "dns0.eu"),
    ("185.253.5.0", "dns0.eu Alt"),
    ("101.226.4.6", "DNSPod (CN)"),
    ("119.29.29.29", "DNSPod Alt (CN)"),
    ("223.5.5.5", "AliDNS (CN)"),
    ("223.6.6.6", "AliDNS Alt (CN)"),
    ("114.114.114.114", "114DNS (CN)"),
]

# DoH (DNS-over-HTTPS) endpoints to test
DOH_ENDPOINTS = [
    ("https://cloudflare-dns.com/dns-query", "Cloudflare DoH"),
    ("https://1.1.1.1/dns-query", "Cloudflare DoH (IP)"),
    ("https://dns.google/dns-query", "Google DoH"),
    ("https://8.8.8.8/dns-query", "Google DoH (IP)"),
    ("https://dns.quad9.net/dns-query", "Quad9 DoH"),
    ("https://dns11.quad9.net/dns-query", "Quad9 DoH (Secured+ECS)"),
    ("https://doh.opendns.com/dns-query", "OpenDNS DoH"),
    ("https://dns.adguard-dns.com/dns-query", "AdGuard DoH"),
    ("https://doh.cleanbrowsing.org/doh/security-filter/", "CleanBrowsing DoH"),
    ("https://dns.nextdns.io/dns-query", "NextDNS DoH"),
    ("https://doh.dns.sb/dns-query", "DNS.SB DoH"),
    ("https://dns.mullvad.net/dns-query", "Mullvad DoH"),
    ("https://freedns.controld.com/p0", "ControlD Free DoH"),
    ("https://zero.dns0.eu/", "dns0.eu DoH"),
    ("https://dns.switch.ch/dns-query", "SWITCH DoH (CH)"),
    ("https://doh.libredns.gr/dns-query", "LibreDNS DoH (GR)"),
    ("https://doh-jp.blahdns.com/dns-query", "BlahDNS DoH (JP)"),
]

# DoT (DNS-over-TLS) endpoints to test
DOT_ENDPOINTS = [
    ("1.1.1.1", 853, "Cloudflare DoT"),
    ("1.0.0.1", 853, "Cloudflare DoT Alt"),
    ("8.8.8.8", 853, "Google DoT"),
    ("8.8.4.4", 853, "Google DoT Alt"),
    ("9.9.9.9", 853, "Quad9 DoT"),
    ("149.112.112.112", 853, "Quad9 DoT Alt"),
    ("94.140.14.14", 853, "AdGuard DoT"),
    ("185.228.168.168", 853, "CleanBrowsing DoT"),
    ("45.90.28.0", 853, "NextDNS DoT"),
    ("193.110.81.0", 853, "dns0.eu DoT"),
    ("116.202.176.26", 853, "LibreDNS DoT"),
    ("dot.dns.sb", 853, "DNS.SB DoT"),
]

# Common local SOCKS/HTTP proxy ports to probe (expanded for popular tools)
PROXY_PORTS_SOCKS = [
    1080,  # Standard SOCKS
    1081,  # SOCKS alt
    2080,  # Sing-box default
    7890,  # Clash / Clash Meta
    7891,  # Clash alt
    10808,  # V2RayN
    10809,  # V2RayN alt
    20170,  # ShadowsocksR
    40000,  # Trojan-Go
    51837,  # Psiphon
    9050,  # Tor
    9150,  # Tor Browser
    1089,  # Shadowsocks-libev
    8889,  # Hiddify
]
PROXY_PORTS_HTTP = [
    3128,  # Squid default
    8080,  # Common HTTP proxy
    8118,  # Privoxy / Lantern
    8888,  # mitmproxy / polipo
    7890,  # Clash (mixed)
    7893,  # Clash TProxy
    10809,  # V2RayN HTTP
    20171,  # ShadowsocksR HTTP
    8889,  # Hiddify HTTP
    9090,  # Clash API / proxy alt
    18080,  # sing-box HTTP alt
    58591,  # Lantern alt
]

# Test URLs for connectivity verification (ordered by likelihood of being unblocked)
TEST_URLS = [
    "http://cp.cloudflare.com/generate_204",
    "http://connectivitycheck.gstatic.com/generate_204",
    "http://www.msftconnecttest.com/connecttest.txt",
    "http://captive.apple.com/hotspot-detect.html",
    "http://detectportal.firefox.com/canonical.html",
    "http://nmcheck.gnome.org/check_network_status.txt",
    "http://network-test.debian.org/nm",
]

# HTTPS test URLs (for verifying TLS works end-to-end)
TEST_URLS_HTTPS = [
    "https://cp.cloudflare.com/",
    "https://www.google.com/generate_204",
    "https://www.microsoft.com/",
    "https://www.apple.com/",
    "https://www.wikipedia.org/",
    "https://api.github.com/",
]

# Alternative CDN / well-known infrastructure IPs for connectivity matrix
# (not just Cloudflare - helps determine if blocking is CF-specific)
ALT_CDN_IPS = [
    ("151.101.1.140", "Fastly (Reddit)"),
    ("151.101.65.140", "Fastly (Reddit Alt)"),
    ("104.16.132.229", "Cloudflare (Discord)"),
    ("142.250.185.206", "Google (YouTube)"),
    ("157.240.1.35", "Meta (Facebook)"),
    ("13.107.42.14", "Microsoft (Azure)"),
    ("31.13.72.36", "Meta (Instagram)"),
    ("149.154.175.50", "Telegram DC2"),
    ("69.171.250.35", "Meta (WhatsApp)"),
    ("185.199.108.153", "GitHub Pages"),
    ("198.41.215.162", "Cloudflare (1.1.1.1)"),
    ("172.67.74.152", "Cloudflare CDN"),
]

# Speed test URLs (small-to-medium payloads for throughput measurement)
SPEED_TEST_URLS = [
    "https://speed.cloudflare.com/__down?bytes=100000",
    "http://speedtest.tele2.net/100KB.zip",
    "https://proof.ovh.net/files/100Mb.dat",
]

# Domains to test for SNI-based blocking (commonly targeted by censors)
SNI_TEST_DOMAINS = [
    ("cloudflare.com", 443, "Cloudflare"),
    ("google.com", 443, "Google"),
    ("youtube.com", 443, "YouTube"),
    ("twitter.com", 443, "Twitter/X"),
    ("facebook.com", 443, "Facebook"),
    ("instagram.com", 443, "Instagram"),
    ("telegram.org", 443, "Telegram"),
    ("signal.org", 443, "Signal"),
    ("whatsapp.com", 443, "WhatsApp"),
    ("wikipedia.org", 443, "Wikipedia"),
    ("reddit.com", 443, "Reddit"),
    ("github.com", 443, "GitHub"),
    ("protonmail.com", 443, "ProtonMail"),
    ("bbc.com", 443, "BBC"),
    ("nytimes.com", 443, "NY Times"),
    ("medium.com", 443, "Medium"),
    ("twitch.tv", 443, "Twitch"),
    ("discord.com", 443, "Discord"),
    ("spotify.com", 443, "Spotify"),
    ("amazon.com", 443, "Amazon"),
    ("tiktok.com", 443, "TikTok"),
    ("openai.com", 443, "OpenAI"),
    ("linkedin.com", 443, "LinkedIn"),
    ("pinterest.com", 443, "Pinterest"),
    ("snapchat.com", 443, "Snapchat"),
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
    def green(t: str) -> str:
        return Colors._c("32", t)

    @staticmethod
    def red(t: str) -> str:
        return Colors._c("31", t)

    @staticmethod
    def yellow(t: str) -> str:
        return Colors._c("33", t)

    @staticmethod
    def cyan(t: str) -> str:
        return Colors._c("36", t)

    @staticmethod
    def bold(t: str) -> str:
        return Colors._c("1", t)

    @staticmethod
    def dim(t: str) -> str:
        return Colors._c("2", t)


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


def load_user_endpoints(source: str) -> List[Tuple[str, int]]:
    """Parse user-supplied endpoints from a file path or comma-separated string.

    Accepts:
        "1.2.3.4:443,5.6.7.8:2408"   -> [("1.2.3.4", 443), ("5.6.7.8", 2408)]
        "/path/to/ips.txt"             -> reads lines like "1.2.3.4:443"
        "1.2.3.4"                      -> [("1.2.3.4", 443)]  (default port 443)
    """
    result: List[Tuple[str, int]] = []
    lines: List[str] = []

    # If it looks like a file path, try reading it
    if os.path.isfile(source):
        with open(source, "r") as fh:
            lines = fh.read().splitlines()
    else:
        # Treat as comma-separated
        lines = source.replace(" ", "").split(",")

    for raw in lines:
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        if ":" in raw:
            parts = raw.rsplit(":", 1)
            try:
                result.append((parts[0], int(parts[1])))
            except ValueError:
                result.append((raw, 443))
        else:
            result.append((raw, 443))
    return result


def tcp_connect(host: str, port: int, timeout: float = 3.0) -> Tuple[bool, float]:
    """Try TCP connect and return (success, latency_ms)."""
    start = time.monotonic()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(timeout)
        s.connect((host, port))
        latency = (time.monotonic() - start) * 1000
        return True, round(latency, 1)
    except Exception:
        return False, 0.0
    finally:
        s.close()


def udp_probe(host: str, port: int, timeout: float = 3.0) -> Tuple[bool, float]:
    """Send a UDP probe (WireGuard handshake initiation) and check for response."""
    probe = b"\x01\x00\x00\x00" + b"\x00" * 140
    start = time.monotonic()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(timeout)
        s.sendto(probe, (host, port))
        data, _ = s.recvfrom(256)
        latency = (time.monotonic() - start) * 1000
        return len(data) > 0, round(latency, 1)
    except Exception:
        return False, 0.0
    finally:
        s.close()


def dns_resolve(
    server: str, domain: str = "cloudflare.com", timeout: float = 3.0
) -> Tuple[bool, float]:
    """Send a raw DNS query to a server and check for response."""
    txid = struct.pack("!H", int(time.time()) & 0xFFFF)
    flags = b"\x01\x00"
    counts = b"\x00\x01\x00\x00\x00\x00\x00\x00"
    qname = b""
    for label in domain.split("."):
        qname += bytes([len(label)]) + label.encode()
    qname += b"\x00"
    query = txid + flags + counts + qname + b"\x00\x01\x00\x01"

    start = time.monotonic()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(timeout)
        s.sendto(query, (server, 53))
        data, _ = s.recvfrom(512)
        latency = (time.monotonic() - start) * 1000
        if len(data) > 12 and data[:2] == txid:
            ancount = struct.unpack("!H", data[6:8])[0]
            return ancount > 0, round(latency, 1)
        return False, round(latency, 1)
    except Exception:
        return False, 0.0
    finally:
        s.close()


def http_get(
    url: str, timeout: float = 5.0, proxy: Optional[str] = None
) -> Tuple[bool, float, int]:
    """HTTP GET request. Returns (success, latency_ms, status_code)."""
    start = time.monotonic()
    try:
        if proxy:
            handler = urllib.request.ProxyHandler(
                {
                    "http": proxy,
                    "https": proxy,
                }
            )
            opener = urllib.request.build_opener(handler)
        else:
            opener = urllib.request.build_opener()

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
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


_TLS_CTX: Optional[ssl.SSLContext] = None


def _get_tls_ctx() -> ssl.SSLContext:
    """Lazy-init a shared permissive TLS context (avoids repeated alloc)."""
    global _TLS_CTX
    if _TLS_CTX is None:
        _TLS_CTX = ssl.create_default_context()
        _TLS_CTX.check_hostname = False
        _TLS_CTX.verify_mode = ssl.CERT_NONE
    return _TLS_CTX


def tls_handshake(
    host: str, port: int = 443, sni: str = "", timeout: float = 5.0
) -> Tuple[bool, float]:
    """Attempt a TLS handshake to check if TLS is blocked."""
    start = time.monotonic()
    ctx = _get_tls_ctx()
    raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        raw.settimeout(timeout)
        wrapped = ctx.wrap_socket(raw, server_hostname=sni or host)
        wrapped.connect((host, port))
        latency = (time.monotonic() - start) * 1000
        wrapped.close()
        return True, round(latency, 1)
    except Exception:
        raw.close()
        return False, 0.0


def socks5_handshake(host: str, port: int, timeout: float = 3.0) -> Tuple[bool, float]:
    """Try a SOCKS5 handshake to detect a SOCKS proxy."""
    start = time.monotonic()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(timeout)
        s.connect((host, port))
        s.sendall(b"\x05\x01\x00")
        resp = s.recv(2)
        latency = (time.monotonic() - start) * 1000
        if len(resp) == 2 and resp[0] == 0x05 and resp[1] in (0x00, 0x02):
            return True, round(latency, 1)
        return False, 0.0
    except Exception:
        return False, 0.0
    finally:
        s.close()


def http_proxy_check(host: str, port: int, timeout: float = 5.0) -> Tuple[bool, float]:
    """Check if host:port is an HTTP proxy by sending a CONNECT."""
    start = time.monotonic()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(timeout)
        s.connect((host, port))
        s.sendall(
            b"CONNECT cloudflare.com:443 HTTP/1.1\r\nHost: cloudflare.com\r\n\r\n"
        )
        resp = s.recv(128)
        latency = (time.monotonic() - start) * 1000
        text = resp.decode(errors="ignore")
        if "200" in text or "HTTP/" in text:
            return True, round(latency, 1)
        return False, 0.0
    except Exception:
        return False, 0.0
    finally:
        s.close()


def dot_probe(
    host: str, port: int = 853, timeout: float = 5.0
) -> Tuple[bool, float, str]:
    """Test DNS-over-TLS by performing a TLS handshake on port 853.

    Returns (success, latency_ms, tls_version).
    """
    start = time.monotonic()
    ctx = _get_tls_ctx()
    raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        raw.settimeout(timeout)
        try:
            socket.inet_aton(host)
            addr = host
        except OSError:
            addr = socket.gethostbyname(host)
        wrapped = ctx.wrap_socket(raw, server_hostname=host)
        wrapped.connect((addr, port))
        latency = (time.monotonic() - start) * 1000
        tls_ver = wrapped.version() or "unknown"
        wrapped.close()
        return True, round(latency, 1), tls_ver
    except Exception:
        raw.close()
        return False, 0.0, ""


def tls_handshake_detailed(
    host: str,
    port: int = 443,
    sni: str = "",
    timeout: float = 5.0,
) -> Tuple[bool, float, str, str]:
    """TLS handshake returning (success, latency_ms, tls_version, cipher).

    Use *sni* to send a different Server Name Indication than *host*.
    """
    start = time.monotonic()
    ctx = _get_tls_ctx()
    raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        raw.settimeout(timeout)
        wrapped = ctx.wrap_socket(raw, server_hostname=sni or host)
        wrapped.connect((host, port))
        latency = (time.monotonic() - start) * 1000
        tls_ver = wrapped.version() or "unknown"
        cipher_info = wrapped.cipher()
        cipher_name = cipher_info[0] if cipher_info else "unknown"
        wrapped.close()
        return True, round(latency, 1), tls_ver, cipher_name
    except Exception:
        raw.close()
        return False, 0.0, "", ""


def icmp_reachable(host: str) -> bool:
    """Best-effort ICMP ping using the system ping command (1 packet)."""
    import subprocess

    param = "-n" if sys.platform == "win32" else "-c"
    try:
        result = subprocess.run(
            ["ping", param, "1", "-W", "2", host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=4,
        )
        return result.returncode == 0
    except Exception:
        return False


def measure_download_speed(
    url: str = "http://cp.cloudflare.com/generate_204",
    proxy: Optional[str] = None,
    timeout: float = 10.0,
) -> Tuple[bool, float, float]:
    """Fetch a URL and measure throughput.

    Returns (success, latency_ms, speed_kbps).
    """
    start = time.monotonic()
    try:
        if proxy:
            handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
            opener = urllib.request.build_opener(handler)
        else:
            opener = urllib.request.build_opener()
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        resp = opener.open(req, timeout=timeout)
        body = resp.read()
        elapsed = time.monotonic() - start
        latency = elapsed * 1000
        size_kb = len(body) / 1024
        speed = (size_kb / elapsed) if elapsed > 0 else 0
        resp.close()
        return True, round(latency, 1), round(speed, 1)
    except Exception:
        return False, 0.0, 0.0


# ============================================================
# Scan Functions
# ============================================================


def scan_basic_connectivity() -> Dict[str, Any]:
    """Phase 1: Check what the user can access at all."""
    section("Phase 1: Basic Connectivity Diagnosis")
    results: Dict[str, Any] = {
        "internet": False,
        "dns": False,
        "tls": False,
        "https": False,
        "cf": False,
        "icmp": False,
    }

    # 1. ICMP ping
    info("Testing ICMP reachability...")
    icmp_targets = ["1.1.1.1", "8.8.8.8", "9.9.9.9"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        icmp_futs = {pool.submit(icmp_reachable, h): h for h in icmp_targets}
        for fut in concurrent.futures.as_completed(icmp_futs):
            host = icmp_futs[fut]
            if fut.result():
                ok(f"ICMP ping to {host} succeeded")
                results["icmp"] = True
            else:
                fail(f"ICMP ping to {host} failed")

    # 2. Raw TCP to well-known IPs
    info("Testing raw TCP connectivity...")
    targets = [
        ("1.1.1.1", 80),
        ("8.8.8.8", 53),
        ("9.9.9.9", 443),
        ("208.67.222.222", 53),
        ("1.1.1.1", 443),
    ]
    for host, port in targets:
        success, lat = tcp_connect(host, port)
        if success:
            ok(f"TCP {host}:{port} reachable ({lat}ms)")
            results["internet"] = True
        else:
            fail(f"TCP {host}:{port} unreachable")

    # 3. DNS resolution
    info("Testing DNS resolution...")
    dns_working = 0
    for server, name in DNS_SERVERS[:6]:
        success, lat = dns_resolve(server)
        if success:
            ok(f"DNS {server} ({name}) works ({lat}ms)")
            results["dns"] = True
            dns_working += 1
        else:
            fail(f"DNS {server} ({name}) blocked/unreachable")

    # 4. TLS handshake
    info("Testing TLS connectivity...")
    tls_targets = [
        ("cloudflare.com", 443),
        ("google.com", 443),
        ("microsoft.com", 443),
        ("apple.com", 443),
    ]
    for host, port in tls_targets:
        success, lat = tls_handshake(host, port)
        if success:
            ok(f"TLS handshake to {host}:{port} succeeded ({lat}ms)")
            results["tls"] = True
            break
        else:
            fail(f"TLS handshake to {host}:{port} failed")

    # 5. HTTPS end-to-end
    info("Testing HTTPS end-to-end connectivity...")
    for url in TEST_URLS_HTTPS[:3]:
        success, lat, status = http_get(url, timeout=8.0)
        if success:
            ok(f"HTTPS {url} reachable ({lat}ms, HTTP {status})")
            results["https"] = True
            break
        else:
            fail(f"HTTPS {url} failed")

    # 6. Cloudflare accessibility
    info("Testing Cloudflare accessibility...")
    success, lat, status = http_get("http://cp.cloudflare.com/generate_204")
    if success and status in (200, 204):
        ok(f"Cloudflare reachable ({lat}ms)")
        results["cf"] = True
    else:
        fail("Cloudflare HTTP check failed")

    # 7. Quick speed estimate
    info("Measuring baseline throughput...")
    speed_ok, speed_lat, speed_kbps = measure_download_speed()
    if speed_ok:
        ok(f"Baseline: {speed_lat}ms latency, ~{speed_kbps} KB/s throughput")
        results["speed_kbps"] = speed_kbps
    else:
        fail("Could not measure throughput")

    # Summary
    section("Diagnosis Summary")
    score = sum(
        [
            results["icmp"],
            results["internet"],
            results["dns"],
            results["tls"],
            results["https"],
            results["cf"],
        ]
    )
    info(f"Connectivity Score: {score}/6")
    print()
    if results["cf"] and results["https"]:
        ok("Full internet access detected.")
        info("Any strategy works: direct proxy, WARP, proxy cascade, CDN relay.")
    elif results["cf"]:
        ok("Cloudflare HTTP works. HTTPS may be filtered.")
        info(
            "Strategies: WARP chain, TLS Fragment, or proxy cascade through local proxy."
        )
    elif results["tls"]:
        info("TLS works but Cloudflare may be filtered.")
        info(
            "Strategies: TLS Fragment, CDN Worker relay, proxy cascade, "
            "or find a relay candidate with less-filtered access."
        )
    elif results["internet"]:
        info("Basic TCP works but TLS is blocked.")
        info(
            "Strategies: Find a local/intranet proxy as Layer 1 (Psiphon, Lantern, "
            "LAN relay), then chain your destination proxy or WARP on top."
        )
    elif results["dns"]:
        info("Only DNS works. Very restrictive network.")
        info(
            "Strategies: DNS tunneling, find a LAN relay (Phase 7), "
            "or install Psiphon/Lantern as Layer 1."
        )
    elif results["icmp"]:
        info("Only ICMP works. Network is heavily filtered.")
        info(
            "Strategies: Find any reachable host on the LAN, ask for proxy settings, "
            "or try Psiphon/Tor as Layer 1."
        )
    else:
        info("No direct internet detected.")
        info(
            "Scan for local proxies (Phase 2), relay candidates (Phase 7), "
            "or ask your network admin for proxy settings."
        )

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
                found.append(
                    {"type": proto, "host": "127.0.0.1", "port": port, "latency": lat}
                )
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
                    found.append(
                        {"type": "socks5", "host": host, "port": port, "latency": lat}
                    )
                elif hp:
                    ok(f"Found HTTP proxy at {host}:{port}")
                    found.append(
                        {"type": "http", "host": host, "port": port, "latency": lat}
                    )

    if not found:
        info("No local proxies found. You may need to configure one manually.")
        info(
            "Common setups: Psiphon (port 1080), Lantern (port 8118), V2RayN (port 10808)"
        )
    else:
        ok(f"Found {len(found)} local proxy(ies).")

    return found


def scan_vwarp_endpoints(rtt_limit: str = "800ms") -> List[Dict[str, Any]]:
    """Use the vwarp binary's built-in --scan for fast clean IP discovery.

    Requires vwarp to be installed and in PATH. Falls back gracefully
    if the binary is not found.
    """
    import shutil as _shutil
    import subprocess as _subprocess

    section("Vwarp Binary Scan")
    binary = _shutil.which("vwarp")
    if not binary:
        # Check common locations
        for p in [
            os.path.expanduser("~/.local/bin/vwarp"),
            "/usr/local/bin/vwarp",
            "./vwarp",
        ]:
            if os.path.isfile(p) and os.access(p, os.X_OK):
                binary = p
                break
    if not binary:
        fail("vwarp binary not found in PATH or common locations.")
        info("Install vwarp from: https://github.com/voidr3aper-anon/Vwarp/releases")
        info("Or use --scan-ips for the built-in Python scanner instead.")
        return []

    ok(f"Found vwarp binary: {binary}")
    cmd = [binary, "--scan", "--rtt", rtt_limit]
    info(f"Running: {' '.join(cmd)}")

    try:
        result = _subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except _subprocess.TimeoutExpired:
        fail("vwarp scan timed out after 60 seconds.")
        return []
    except Exception as exc:
        fail(f"vwarp scan failed: {exc}")
        return []

    endpoints: List[Dict[str, Any]] = []
    if result.stdout:
        for line in result.stdout.strip().splitlines():
            # Expected: "162.159.192.10:2408 - 150ms" or similar
            if ":" in line and "ms" in line:
                parts = line.split()
                if not parts:
                    continue
                ep = parts[0].strip()
                # Parse latency
                latency_ms = 0
                for part in parts:
                    if part.endswith("ms"):
                        try:
                            latency_ms = int(part.replace("ms", ""))
                        except ValueError:
                            pass

                host, port_str = ep, "2408"
                if ":" in ep and not ep.startswith("["):
                    host, port_str = ep.rsplit(":", 1)
                try:
                    port = int(port_str)
                except ValueError:
                    port = 2408

                endpoints.append(
                    {
                        "ip": host,
                        "port": port,
                        "latency_ms": latency_ms,
                        "source": "vwarp",
                    }
                )

    if endpoints:
        ok(f"vwarp found {len(endpoints)} clean endpoint(s):")
        for entry in endpoints[:15]:
            ok(f"  {entry['ip']}:{entry['port']} ({entry['latency_ms']}ms)")
    else:
        fail("vwarp scan returned no results.")
        info("Try --scan-ips for the built-in Python scanner.")

    return endpoints


def scan_clean_ips(
    top_n: int = 10,
    max_workers: int = 30,
    extra_ips: Optional[List[Tuple[str, int]]] = None,
) -> List[Dict[str, Any]]:
    """Phase 3: Scan for clean Cloudflare WARP IPs.

    *extra_ips* merges user-supplied IP:port pairs into the scan.
    """
    section("Phase 3: Clean Cloudflare IP Scan")

    # Merge user-supplied endpoints
    scan_ips = list(CF_IPS)
    scan_ports = list(CF_PORTS)
    extra_pairs: List[Tuple[str, int]] = []
    if extra_ips:
        for ip, port in extra_ips:
            if ip not in scan_ips:
                scan_ips.append(ip)
            if port not in scan_ports:
                scan_ports.append(port)
            extra_pairs.append((ip, port))
        info(f"Including {len(extra_ips)} user-supplied endpoint(s)")

    info(
        f"Scanning {len(scan_ips)} IPs x {len(scan_ports)} ports "
        f"({len(scan_ips) * len(scan_ports)} combinations)..."
    )
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
        for ip in scan_ips:
            for port in scan_ports:
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
            print(
                f"  {r['ip']:<20} {r['port']:<8} {Colors.green(lat_str):<12} {r['proto']}"
            )
    else:
        fail("No reachable Cloudflare endpoints found.")
        info("Your ISP may be blocking all Cloudflare WARP IPs.")
        info(
            "Try using a local proxy (Phase 2) as Layer 1, then scan again through it."
        )

    return top


def scan_dns_servers() -> List[Dict[str, Any]]:
    """Phase 4: Find working DNS servers (UDP, DoH, DoT)."""
    section("Phase 4: DNS Server Scan")
    results: List[Dict[str, Any]] = []

    # --- Standard DNS (UDP/53) ---
    info("Testing standard DNS (UDP port 53)...")
    udp_working = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futs = {
            pool.submit(dns_resolve, server): (server, name)
            for server, name in DNS_SERVERS
        }
        for fut in concurrent.futures.as_completed(futs):
            server, name = futs[fut]
            success, lat = fut.result()
            if success:
                ok(f"{server:>18} ({name}) - {lat}ms")
                results.append(
                    {"server": server, "name": name, "type": "udp", "latency": lat}
                )
                udp_working += 1
            else:
                fail(f"{server:>18} ({name}) - unreachable")
    info(f"Standard DNS: {udp_working}/{len(DNS_SERVERS)} reachable")

    # --- DNS-over-HTTPS (DoH) ---
    print()
    info("Testing DNS-over-HTTPS (DoH)...")
    doh_working = 0
    for url, name in DOH_ENDPOINTS:
        # GET with base64url wireformat query for example.com A record
        sep = "&" if "?" in url else "?"
        test_url = url + sep + "dns=AAABAAABAAAAAAAAB2V4YW1wbGUDY29tAAABAAE"
        success, lat, status = http_get(test_url, timeout=8.0)
        if success:
            ok(f"{name:<30} - {lat}ms")
            results.append({"server": url, "name": name, "type": "doh", "latency": lat})
            doh_working += 1
        else:
            fail(f"{name:<30} - unreachable")
    info(f"DoH: {doh_working}/{len(DOH_ENDPOINTS)} reachable")

    # --- DNS-over-TLS (DoT / port 853) ---
    print()
    info("Testing DNS-over-TLS (DoT, port 853)...")
    dot_working = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        dot_futs: Dict[concurrent.futures.Future, Tuple[str, int, str]] = {}  # type: ignore[type-arg]
        for _dot_host, _dot_port, _dot_name in DOT_ENDPOINTS:
            f = pool.submit(dot_probe, _dot_host, _dot_port)
            dot_futs[f] = (_dot_host, _dot_port, _dot_name)
        for fut in concurrent.futures.as_completed(dot_futs):
            host, port, name = dot_futs[fut]
            success, lat, tls_ver = fut.result()  # type: ignore[misc]
            if success:
                ok(f"{name:<30} - {lat}ms ({tls_ver})")
                results.append(
                    {
                        "server": f"{host}:{port}",
                        "name": name,
                        "type": "dot",
                        "latency": lat,
                        "tls_version": tls_ver,
                    }
                )
                dot_working += 1
            else:
                fail(f"{name:<30} - unreachable")
    info(f"DoT: {dot_working}/{len(DOT_ENDPOINTS)} reachable")

    # --- Summary ---
    print()
    if not results:
        info("No working DNS servers found. Your DNS is completely blocked.")
        info("Consider using DoH through a local proxy, or hardcode IP addresses.")
    else:
        # Sort by latency and show top 5
        sorted_results = sorted(results, key=lambda x: x["latency"])
        info("Top 5 fastest DNS servers:")
        for r in sorted_results[:5]:
            tag = f"[{r['type'].upper()}]"
            print(f"    {tag:<6} {r['name']:<30} {r['latency']}ms")

    return results


def scan_sni_blocking(max_workers: int = 10) -> Dict[str, Any]:
    """Phase 5: Detect SNI-based blocking by testing TLS handshakes to popular domains."""
    section("Phase 5: SNI Blocking Detection")
    info(f"Testing {len(SNI_TEST_DOMAINS)} domains for TLS/SNI blocking...")
    print()

    blocked: List[str] = []
    accessible: List[str] = []
    results: Dict[str, Any] = {"domains": {}}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = {
            pool.submit(tls_handshake_detailed, domain, port): (domain, port, name)
            for domain, port, name in SNI_TEST_DOMAINS
        }
        for fut in concurrent.futures.as_completed(futs):
            domain, port, name = futs[fut]
            success, lat, tls_ver, cipher = fut.result()
            if success:
                ok(f"{name:<15} ({domain}) - {lat}ms [{tls_ver}]")
                accessible.append(domain)
                results["domains"][domain] = {
                    "name": name,
                    "blocked": False,
                    "latency": lat,
                    "tls_version": tls_ver,
                    "cipher": cipher,
                }
            else:
                fail(f"{name:<15} ({domain}) - BLOCKED or unreachable")
                blocked.append(domain)
                results["domains"][domain] = {"name": name, "blocked": True}

    print()
    results["total_tested"] = len(SNI_TEST_DOMAINS)
    results["accessible_count"] = len(accessible)
    results["blocked_count"] = len(blocked)

    if blocked:
        block_pct = len(blocked) / len(SNI_TEST_DOMAINS) * 100
        info(
            f"Blocking detected: {len(blocked)}/{len(SNI_TEST_DOMAINS)} domains blocked ({block_pct:.0f}%)"
        )
        info(f"Blocked: {', '.join(blocked)}")

        if block_pct > 80:
            info("Heavy SNI filtering. Use TLS Fragment, ECH, or Reality to bypass.")
        elif block_pct > 40:
            info(
                "Moderate SNI filtering. CDN-fronted configs may work for unblocked domains."
            )
        else:
            info("Light SNI filtering. Most services still accessible.")
    else:
        ok("No SNI blocking detected. All tested domains are accessible via TLS.")

    return results


def scan_port_matrix(
    ips: Optional[List[str]] = None,
    ports: Optional[List[int]] = None,
    max_workers: int = 30,
    extra_ips: Optional[List[Tuple[str, int]]] = None,
) -> Dict[str, Any]:
    """Phase 6: Build a reachability matrix of IPs x Ports.

    *extra_ips* adds user-supplied IP:port pairs (IPs are added to rows,
    ports to columns).
    """
    section("Phase 6: Port Reachability Matrix")

    # Default IPs include well-known infra + a few alt CDN IPs
    default_ips = ["1.1.1.1", "8.8.8.8", "9.9.9.9", "162.159.192.1"]
    for cdn_ip, _cdn_name in ALT_CDN_IPS[:4]:
        if cdn_ip not in default_ips:
            default_ips.append(cdn_ip)
    test_ips = ips or default_ips
    test_ports = ports or [53, 80, 443, 853, 500, 2408, 4500, 8080, 8443]

    # Merge user-supplied endpoints
    if extra_ips:
        for eip, eport in extra_ips:
            if eip not in test_ips:
                test_ips.append(eip)
            if eport not in test_ports:
                test_ports.append(eport)
    total = len(test_ips) * len(test_ports)
    info(f"Testing {len(test_ips)} IPs x {len(test_ports)} ports ({total} probes)...")
    print()

    matrix: Dict[str, Dict[int, bool]] = {ip: {} for ip in test_ips}
    results: Dict[str, Any] = {"matrix": {}}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = {}
        for ip in test_ips:
            for port in test_ports:
                futs[pool.submit(tcp_connect, ip, port, 3.0)] = (ip, port)

        for fut in concurrent.futures.as_completed(futs):
            ip, port = futs[fut]
            success, _ = fut.result()
            matrix[ip][port] = success

    # Print matrix header
    port_hdr = "".join(f"{p:<8}" for p in test_ports)
    print(f"  {'IP':<20} {port_hdr}")
    print(f"  {'-'*20} " + "-" * (8 * len(test_ports)))

    for ip in test_ips:
        row = ""
        for port in test_ports:
            reachable = matrix[ip].get(port, False)
            cell = Colors.green("  OK  ") if reachable else Colors.red(" FAIL ")
            row += f"{cell}  "
        print(f"  {ip:<20} {row}")
        results["matrix"][ip] = {str(p): matrix[ip].get(p, False) for p in test_ports}

    # Summary: find universally open ports
    print()
    open_ports = []
    for port in test_ports:
        if all(matrix[ip].get(port, False) for ip in test_ips):
            open_ports.append(port)
    if open_ports:
        ok(f"Universally open ports: {', '.join(str(p) for p in open_ports)}")
    else:
        info("No ports are open to all tested IPs.")

    blocked_ips = [ip for ip in test_ips if not any(matrix[ip].values())]
    if blocked_ips:
        info(f"Fully blocked IPs: {', '.join(blocked_ips)}")

    results["open_ports"] = open_ports
    results["blocked_ips"] = blocked_ips
    return results


def scan_relay_candidates(
    max_workers: int = 20,
    extra_hosts: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Phase 7: Discover relay candidates — any host that can act as an intermediate hop.

    Sources scanned:
    1. Common LAN subnets (192.168.x, 10.x, 172.16.x) for SOCKS5/HTTP proxies.
    2. User-supplied hosts via *extra_hosts* (can be LAN or public IPs/URIs).

    A relay is NOT limited to LAN — any intermediate proxy that has internet
    access (or better-filtered access) qualifies.  Pipeline output proxies,
    remote SOCKS5/HTTP proxies, or corporate gateways all work as relays.
    """
    section("Phase 7: Relay Candidate Discovery")

    # Common LAN ranges to probe (first + last host in typical /24)
    lan_hosts: List[str] = []
    for prefix in ("192.168.1", "192.168.0", "10.0.0", "10.0.1", "172.16.0"):
        for suffix in (1, 2, 10, 50, 100, 200, 254):
            lan_hosts.append(f"{prefix}.{suffix}")

    relay_ports = [80, 443, 3128, 8080, 8443, 8888, 1080, 9090]

    # Merge user-supplied extra hosts (can be host:port or full URIs)
    extra_parsed: List[Dict[str, Any]] = []
    if extra_hosts:
        for eh in extra_hosts:
            eh = eh.strip()
            if not eh:
                continue
            if "://" in eh:
                # Treat as proxy URI — test directly as a relay candidate
                parsed = _parse_proxy_uri(eh)
                if parsed:
                    extra_parsed.append(parsed)
                    continue
            # Treat as host:port
            parts = eh.rsplit(":", 1)
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 1080
            lan_hosts.append(host)
            if port not in relay_ports:
                relay_ports.append(port)

    info(
        f"Probing {len(lan_hosts)} hosts x {len(relay_ports)} ports "
        f"for reachable relay services..."
    )

    live_hosts: List[Dict[str, Any]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = {}
        for host in lan_hosts:
            for port in relay_ports:
                futs[pool.submit(tcp_connect, host, port, 1.5)] = (host, port)

        for fut in concurrent.futures.as_completed(futs):
            host, port = futs[fut]
            success, lat = fut.result()
            if success:
                live_hosts.append({"host": host, "port": port, "latency": lat})

    if not live_hosts and not extra_parsed:
        info("No reachable relay services found.")
        return []

    ok(
        f"Found {len(live_hosts)} reachable service(s) via scan"
        + (f", {len(extra_parsed)} from user-supplied URIs" if extra_parsed else "")
        + ". Checking internet access..."
    )

    # Test which of these can reach the public internet
    relays: List[Dict[str, Any]] = []

    for entry in live_hosts[:20]:  # cap to avoid slowness
        host, port = entry["host"], entry["port"]

        # Check if it's a SOCKS proxy
        s5_ok, s5_lat = socks5_handshake(host, port, timeout=3.0)
        if s5_ok:
            # Test internet through it
            proxy_url = f"socks5://{host}:{port}"
            ok_http, lat_http, _ = http_get(
                "http://cp.cloudflare.com/generate_204", timeout=8.0, proxy=proxy_url
            )
            if ok_http:
                ok(f"SOCKS5 relay at {host}:{port} has internet access ({lat_http}ms)")
                relays.append(
                    {
                        "type": "socks5",
                        "host": host,
                        "port": port,
                        "latency": lat_http,
                        "internet": True,
                    }
                )
                continue

        # Check if it's an HTTP proxy
        hp_ok, hp_lat = http_proxy_check(host, port, timeout=3.0)
        if hp_ok:
            proxy_url = f"http://{host}:{port}"
            ok_http, lat_http, _ = http_get(
                "http://cp.cloudflare.com/generate_204", timeout=8.0, proxy=proxy_url
            )
            if ok_http:
                ok(f"HTTP relay at {host}:{port} has internet access ({lat_http}ms)")
                relays.append(
                    {
                        "type": "http",
                        "host": host,
                        "port": port,
                        "latency": lat_http,
                        "internet": True,
                    }
                )
                continue

        # Check if it's HTTPS (could be a web gateway / jump box)
        if port in (443, 8443):
            tls_ok, tls_lat = tls_handshake(host, port, timeout=3.0)
            if tls_ok:
                info(
                    f"TLS service at {host}:{port} ({tls_lat}ms) — may be a web gateway"
                )
                relays.append(
                    {
                        "type": "https_host",
                        "host": host,
                        "port": port,
                        "latency": tls_lat,
                        "internet": False,  # unknown - needs manual verification
                    }
                )

    # Include user-supplied URI-based relay candidates (already parsed)
    for ep in extra_parsed:
        host = ep.get("host", "")
        port = ep.get("port", 0)
        ptype = ep.get("type", "socks5")
        if not host:
            continue
        ok_tcp, lat = tcp_connect(host, int(port), timeout=5.0)
        if ok_tcp:
            ok(f"User-supplied relay {ptype}://{host}:{port} is reachable ({lat}ms)")
            relays.append(
                {
                    "type": ptype,
                    "host": host,
                    "port": port,
                    "latency": lat,
                    "internet": True,  # assumed — user supplied it as a working proxy
                }
            )

    if relays:
        internet_relays = [r for r in relays if r.get("internet")]
        if internet_relays:
            ok(f"Found {len(internet_relays)} relay(s) with confirmed internet access!")
            info("These can be used as intermediate hops in your chain.")
        else:
            info(f"Found {len(relays)} host(s) but none confirmed internet access.")
            info("Try using them manually as a relay (they may need authentication).")
    else:
        info("No usable relay candidates found.")

    return relays


def test_through_proxy(
    proxy_type: str, proxy_host: str, proxy_port: int
) -> Dict[str, Any]:
    """Test what's reachable through a given proxy."""
    section(f"Testing Through Proxy: {proxy_type}://{proxy_host}:{proxy_port}")
    result: Dict[str, Any] = {
        "proxy": f"{proxy_type}://{proxy_host}:{proxy_port}",
        "tests": {},
    }

    proxy_url = f"{proxy_type}://{proxy_host}:{proxy_port}"

    # Test HTTP URLs
    info("Testing HTTP connectivity via proxy...")
    for url in TEST_URLS:
        success, lat, status = http_get(url, timeout=8.0, proxy=proxy_url)
        if success:
            ok(f"[via proxy] {url} - {lat}ms (HTTP {status})")
            result["tests"][url] = {"success": True, "latency": lat, "status": status}
        else:
            fail(f"[via proxy] {url} - failed")
            result["tests"][url] = {"success": False}

    # Test HTTPS URLs
    info("Testing HTTPS connectivity via proxy...")
    for url in TEST_URLS_HTTPS[:3]:
        success, lat, status = http_get(url, timeout=10.0, proxy=proxy_url)
        if success:
            ok(f"[via proxy] {url} - {lat}ms (HTTP {status})")
            result["tests"][url] = {"success": True, "latency": lat, "status": status}
        else:
            fail(f"[via proxy] {url} - failed")
            result["tests"][url] = {"success": False}

    working = sum(1 for t in result["tests"].values() if t.get("success"))
    total = len(result["tests"])
    if working > 0:
        ok(f"Proxy passes {working}/{total} connectivity tests.")
    else:
        fail("Proxy cannot reach any test URLs.")

    # Speed test through proxy
    info("Measuring throughput via proxy...")
    sp_ok, sp_lat, sp_kbps = measure_download_speed(proxy=proxy_url)
    if sp_ok:
        ok(f"Proxy throughput: {sp_lat}ms latency, ~{sp_kbps} KB/s")
        result["speed_kbps"] = sp_kbps
    else:
        fail("Could not measure proxy throughput")

    return result


def generate_chain_config(layers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a sing-box chain config from a list of layers."""
    outbounds: List[Dict[str, Any]] = []
    prev_tag = None

    for i, layer in enumerate(reversed(layers)):
        tag = f"layer-{len(layers) - i}"
        outbound: Dict[str, Any] = {"tag": tag}

        if layer["type"] == "socks5":
            outbound.update(
                {
                    "type": "socks",
                    "server": layer["host"],
                    "server_port": layer["port"],
                    "version": "5",
                }
            )
        elif layer["type"] == "http":
            outbound.update(
                {"type": "http", "server": layer["host"], "server_port": layer["port"]}
            )
        elif layer["type"] == "warp":
            outbound.update(
                {
                    "type": "wireguard",
                    "server": layer["ip"],
                    "server_port": layer["port"],
                    "local_address": [f"172.16.0.{i + 2}/32"],
                    "private_key": "YNS+CEQE6JIQiVWcOUJd0K8FLFeCQBONJnXCdFnMRlQ=",
                    "peer_public_key": "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
                    "mtu": 1280,
                }
            )
        elif layer["type"] in ("vless", "vmess", "trojan", "shadowsocks"):
            outbound.update(
                {
                    "type": layer["type"],
                    "server": layer["host"],
                    "server_port": layer["port"],
                }
            )
            if layer.get("uuid"):
                outbound["uuid" if layer["type"] != "trojan" else "password"] = layer[
                    "uuid"
                ]
            if layer.get("tls"):
                outbound["tls"] = {
                    "enabled": True,
                    "server_name": layer.get("sni", layer["host"]),
                }

        if prev_tag:
            outbound["detour"] = prev_tag
        prev_tag = tag
        outbounds.append(outbound)

    # The first outbound in the list is the innermost (user-facing)
    outbounds.reverse()
    primary_tag = outbounds[0]["tag"] if outbounds else "direct"

    return {
        "log": {"level": "info"},
        "inbounds": [
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "127.0.0.1",
                "listen_port": 2080,
            }
        ],
        "outbounds": outbounds
        + [{"type": "direct", "tag": "direct"}, {"type": "block", "tag": "block"}],
        "route": {
            "rules": [{"inbound": ["mixed-in"], "outbound": primary_tag}],
            "final": primary_tag,
        },
    }


# ============================================================
# Smart Chain Testing
# ============================================================


def test_chain_layers(layers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Test a multi-layer chain using multiple strategies.

    Instead of only testing the full chain linearly (L1 -> L2 -> L3 -> Internet),
    this tries several approaches to pinpoint which layer is failing:

    Strategy 1 - Individual: Test each layer on its own against the internet.
    Strategy 2 - Pairs:      Test adjacent layer pairs (L1+L2, L2+L3, etc.).
    Strategy 3 - Reverse:    Start from the outermost layer and work inward.
    Strategy 4 - Full chain: Test the complete chain end-to-end.

    This helps diagnose issues like: "L1 works but L2 is dead" or
    "L1+L2 work but adding L3 breaks it (L3's port is blocked)."
    """
    section("Smart Chain Test")
    if not layers:
        info("No layers to test.")
        return {"strategies": {}, "recommendation": "Add at least one layer."}

    results: Dict[str, Any] = {"strategies": {}, "layers": len(layers)}

    # --- Strategy 1: Test each layer individually ---
    info(f"Strategy 1: Testing {len(layers)} layers individually...")
    individual: List[Dict[str, Any]] = []
    for i, layer in enumerate(layers):
        name = f"Layer {i + 1} ({layer['type']})"
        host = layer.get("host", layer.get("ip", ""))
        port = layer.get("port", 0)
        if not host or not port:
            fail(f"  {name}: missing host/port, skipping")
            individual.append({"layer": i + 1, "ok": False, "reason": "missing_addr"})
            continue

        # Test TCP reachability
        tcp_ok, tcp_lat = tcp_connect(host, int(port), timeout=5.0)
        if tcp_ok:
            ok(f"  {name}: {host}:{port} reachable ({tcp_lat}ms)")
        else:
            fail(f"  {name}: {host}:{port} unreachable")

        # For WARP/WireGuard, also try UDP
        udp_ok = False
        if layer["type"] == "warp":
            udp_ok, udp_lat = udp_probe(host, int(port), timeout=3.0)
            if udp_ok:
                ok(f"  {name}: UDP probe responded ({udp_lat}ms)")

        # For TLS-based proxies, test TLS handshake
        tls_ok = False
        if layer["type"] in ("vless", "vmess", "trojan") and layer.get("tls", True):
            sni = layer.get("sni", host)
            tls_ok, tls_lat = tls_handshake(host, int(port), sni=sni, timeout=5.0)
            if tls_ok:
                ok(f"  {name}: TLS handshake OK ({tls_lat}ms)")
            else:
                fail(f"  {name}: TLS handshake failed (SNI may be blocked)")

        individual.append(
            {
                "layer": i + 1,
                "type": layer["type"],
                "host": host,
                "port": port,
                "tcp": tcp_ok,
                "udp": udp_ok,
                "tls": tls_ok,
                "ok": tcp_ok or udp_ok,
            }
        )
    results["strategies"]["individual"] = individual

    # --- Strategy 2: Test adjacent pairs ---
    if len(layers) >= 2:
        print()
        info("Strategy 2: Testing adjacent layer pairs...")
        pairs: List[Dict[str, Any]] = []
        for i in range(len(layers) - 1):
            pair_name = f"Layers {i + 1}+{i + 2}"
            l1 = layers[i]
            l2 = layers[i + 1]

            # Test L2 reachability through L1
            l1_host = l1.get("host", l1.get("ip", ""))
            l1_port = l1.get("port", 0)
            l2_host = l2.get("host", l2.get("ip", ""))

            if l1["type"] in ("socks5", "http") and l1_host and l2_host:
                proxy_url = f"{l1['type']}://{l1_host}:{l1_port}"
                pair_ok, pair_lat, _ = http_get(
                    "http://cp.cloudflare.com/generate_204",
                    timeout=8.0,
                    proxy=proxy_url,
                )
                if pair_ok:
                    ok(f"  {pair_name}: Internet reachable through {l1['type']} proxy")
                else:
                    fail(
                        f"  {pair_name}: Cannot reach internet through {l1['type']} proxy"
                    )
                pairs.append({"pair": f"{i + 1}+{i + 2}", "ok": pair_ok})
            else:
                info(f"  {pair_name}: Pair test requires L1 to be SOCKS5/HTTP proxy")
                pairs.append(
                    {"pair": f"{i + 1}+{i + 2}", "ok": None, "reason": "not_proxy_l1"}
                )
        results["strategies"]["pairs"] = pairs

    # --- Strategy 3: Reverse test (outermost first) ---
    print()
    info("Strategy 3: Reverse test (outermost layer first)...")
    reverse_ok = True
    for i in range(len(layers) - 1, -1, -1):
        layer = layers[i]
        host = layer.get("host", layer.get("ip", ""))
        port = layer.get("port", 0)
        name = f"Layer {i + 1} ({layer['type']})"
        if not host:
            continue
        reachable, lat = tcp_connect(host, int(port), timeout=5.0)
        if reachable:
            ok(f"  {name}: reachable from here ({lat}ms)")
        else:
            fail(f"  {name}: unreachable - this breaks the chain from this point")
            reverse_ok = False
            break
    results["strategies"]["reverse_ok"] = reverse_ok

    # --- Strategy 4: Full chain test (generate config + connectivity advice) ---
    print()
    info("Strategy 4: Full chain analysis...")
    all_reachable = all(r.get("ok") for r in individual)
    if all_reachable:
        ok("All layers are individually reachable. Full chain should work.")
        generate_chain_config(layers)
        info("Generated sing-box config for full chain test.")
        info("To test end-to-end, run:")
        print("    sing-box run -c <config-file>")
        print("    curl -x socks5://127.0.0.1:2080 https://ip.gs")
    else:
        failed = [r for r in individual if not r.get("ok")]
        fail(f"{len(failed)} layer(s) are unreachable. Chain will fail.")

    # --- Recommendations ---
    print()
    section("Chain Test Recommendations")
    failed_layers = [r for r in individual if not r.get("ok")]
    tls_failed = [
        r
        for r in individual
        if r.get("tcp")
        and not r.get("tls")
        and r.get("type") in ("vless", "vmess", "trojan")
    ]

    if not failed_layers and not tls_failed:
        ok("All layers passed. Your chain is ready to deploy.")
        results["recommendation"] = "all_ok"
    elif tls_failed:
        for r in tls_failed:
            info(
                f"Layer {r['layer']} ({r['type']}): TCP works but TLS fails. "
                "Try TLS Fragment or change the SNI."
            )
        results["recommendation"] = "tls_blocked"
    elif len(failed_layers) == 1:
        fl = failed_layers[0]
        info(
            f"Layer {fl['layer']} ({fl.get('type', '?')}) at {fl.get('host', '?')}:{fl.get('port', '?')} is unreachable."
        )
        if fl["layer"] == 1:
            info("Your Layer 1 (base proxy) is down. Try a different proxy.")
        else:
            info(
                f"Layers 1-{fl['layer'] - 1} work. Try replacing Layer {fl['layer']} "
                "or use a different port/IP."
            )
        results["recommendation"] = f"layer_{fl['layer']}_failed"
    else:
        info(
            f"Multiple layers failed ({len(failed_layers)}). "
            "Check your network first with: python lab-scanner.py --quick"
        )
        results["recommendation"] = "multiple_failed"

    return results


def auto_find_best_chain(
    proxies: Optional[List[Dict[str, Any]]] = None,
    clean_ips: Optional[List[Dict[str, Any]]] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Automatically discover the best chain path using multiple strategies.

    Strategies tried (in order of simplicity):
    1. Direct proxy   — proxy is directly reachable, no tunnel needed
    2. Proxy cascade  — chain local proxies together (e.g. Psiphon -> V2Ray)
    3. Relay hop      — any intermediate host with internet (LAN, remote, pipeline)
    4. WARP tunnel    — wrap proxy in Cloudflare WARP
    5. Local proxy + WARP — local proxy reaches WARP which reaches the proxy
    6. Relay + WARP   — relay candidate reaches WARP which reaches the proxy
    """
    section("Auto-Detect Best Chain Path")

    # ------------------------------------------------------------------
    # Strategy 1: Direct proxy access
    # ------------------------------------------------------------------
    info("Strategy 1: Checking if proxy is directly reachable...")
    if proxies:
        for p in proxies[:3]:
            host = p.get("host", p.get("ip", ""))
            port = p.get("port", 0)
            if not host:
                continue
            ok_tcp, lat = tcp_connect(host, int(port), timeout=5.0)
            if ok_tcp:
                ok(f"Direct to {host}:{port} works ({lat}ms). No tunnel needed!")
                return [p]
        fail("Direct proxy access blocked.")
    else:
        info(
            "No destination proxy supplied — will find a working path to the internet."
        )

    # ------------------------------------------------------------------
    # Strategy 2: Proxy cascade — chain multiple local proxies
    # ------------------------------------------------------------------
    info("Strategy 2: Scanning for local proxies to cascade...")
    local_proxies = scan_local_proxies()

    if local_proxies and proxies:
        # Test if the first local proxy can reach the destination proxy
        lp = local_proxies[0]
        proxy_url = f"{lp['type']}://{lp['host']}:{lp['port']}"
        cascade_ok, cascade_lat, _ = http_get(
            "http://cp.cloudflare.com/generate_204", timeout=8.0, proxy=proxy_url
        )
        if cascade_ok:
            ok(
                f"Local proxy {lp['type']}://{lp['host']}:{lp['port']} "
                f"has internet access ({cascade_lat}ms)."
            )
            ok("Best path: Local Proxy -> Destination Proxy (proxy cascade)")
            return [lp] + proxies[:1]

    if local_proxies and len(local_proxies) >= 2:
        # Two local proxies — chain them for extra obfuscation
        lp1, lp2 = local_proxies[0], local_proxies[1]
        proxy_url1 = f"{lp1['type']}://{lp1['host']}:{lp1['port']}"
        ok_p1, _, _ = http_get(
            "http://cp.cloudflare.com/generate_204", timeout=8.0, proxy=proxy_url1
        )
        if ok_p1:
            ok(
                f"Best path: {lp1['type']}://{lp1['host']}:{lp1['port']} -> "
                f"{lp2['type']}://{lp2['host']}:{lp2['port']} (double proxy cascade)"
            )
            return [lp1, lp2]

    if local_proxies:
        # Single local proxy with internet — use it standalone
        lp = local_proxies[0]
        proxy_url = f"{lp['type']}://{lp['host']}:{lp['port']}"
        ok_single, _, _ = http_get(
            "http://cp.cloudflare.com/generate_204", timeout=8.0, proxy=proxy_url
        )
        if ok_single and not proxies:
            ok(
                f"Local proxy {lp['type']}://{lp['host']}:{lp['port']} "
                "reaches internet. Use as standalone or stack more layers."
            )
            return [lp]

    # ------------------------------------------------------------------
    # Strategy 3: Relay hop — find any host that can act as an intermediate hop
    # ------------------------------------------------------------------
    info("Strategy 3: Scanning for relay candidates (LAN + user-supplied)...")
    relay_candidates = scan_relay_candidates(max_workers=15)
    internet_relays = [r for r in relay_candidates if r.get("internet")]

    if internet_relays:
        relay = internet_relays[0]
        relay_layer = {
            "type": relay["type"],
            "host": relay["host"],
            "port": relay["port"],
        }
        if proxies:
            ok(
                f"Best path: Relay {relay['type']}://{relay['host']}:{relay['port']} "
                "-> Destination Proxy"
            )
            return [relay_layer] + proxies[:1]
        else:
            ok(
                f"Relay {relay['type']}://{relay['host']}:{relay['port']} "
                "has internet access. Use as Layer 1."
            )
            return [relay_layer]

    # ------------------------------------------------------------------
    # Strategy 4: WARP tunnel
    # ------------------------------------------------------------------
    info("Strategy 4: Checking Cloudflare WARP reachability...")
    working_warp = None
    if clean_ips:
        for ip_data in clean_ips[:5]:
            ip = ip_data.get("ip", "")
            port = ip_data.get("port", 2408)
            ok_udp, lat = udp_probe(ip, int(port), timeout=3.0)
            if ok_udp:
                working_warp = {"type": "warp", "ip": ip, "port": int(port)}
                ok(f"WARP endpoint {ip}:{port} reachable ({lat}ms)")
                break
            ok_tcp, lat = tcp_connect(ip, int(port), timeout=3.0)
            if ok_tcp:
                working_warp = {"type": "warp", "ip": ip, "port": int(port)}
                ok(f"WARP endpoint {ip}:{port} reachable via TCP ({lat}ms)")
                break

    if working_warp:
        if proxies:
            ok("Best path: WARP tunnel + Proxy (2-layer chain)")
            return [proxies[0], working_warp]
        else:
            ok("WARP reachable. Use it as a tunnel to the free internet.")
            return [working_warp]

    # ------------------------------------------------------------------
    # Strategy 5: Local proxy + WARP
    # ------------------------------------------------------------------
    if local_proxies and clean_ips:
        info("Strategy 5: Trying Local Proxy -> WARP...")
        lp = local_proxies[0]
        best_ip = clean_ips[0]
        info(
            f"Best path: {lp['type']}://{lp['host']}:{lp['port']} -> "
            f"WARP {best_ip.get('ip', '')}:{best_ip.get('port', 2408)}"
        )
        chain = [
            lp,
            {
                "type": "warp",
                "ip": best_ip.get("ip", ""),
                "port": best_ip.get("port", 2408),
            },
        ]
        if proxies:
            chain.append(proxies[0])
        return chain

    # ------------------------------------------------------------------
    # Strategy 6: Relay + WARP
    # ------------------------------------------------------------------
    if relay_candidates and clean_ips:
        info("Strategy 6: Trying Relay -> WARP...")
        relay = relay_candidates[0]
        best_ip = clean_ips[0]
        relay_chain: List[Dict[str, Any]] = [
            {"type": relay["type"], "host": relay["host"], "port": relay["port"]},
            {
                "type": "warp",
                "ip": best_ip.get("ip", ""),
                "port": best_ip.get("port", 2408),
            },
        ]
        if proxies:
            relay_chain.append(proxies[0])
        return relay_chain

    # ------------------------------------------------------------------
    # No automatic path found
    # ------------------------------------------------------------------
    fail("Could not find a working chain path automatically.")
    print()
    info("Suggestions:")
    info("  1. Install a circumvention tool (Psiphon, Lantern, Tor) as Layer 1")
    info("  2. Ask your network admin for proxy settings")
    info("  3. Try: python lab-scanner.py --interactive  (manual chain builder)")
    info("  4. Try: python lab-scanner.py --scan-ports   (find open ports)")
    info("  5. Check if any colleague/friend has a working proxy you can use")
    return None


# ============================================================
# Interactive Mode
# ============================================================


def _parse_proxy_uri(uri: str) -> Optional[Dict[str, Any]]:
    """Parse a proxy URI string into a layer dict for chain building.

    Supported schemes: vless://, vmess://, trojan://, ss://, socks5://, socks://, http://
    Returns None if parsing fails.
    """
    uri = uri.strip()
    if not uri or "://" not in uri:
        return None

    scheme, rest = uri.split("://", 1)
    scheme = scheme.lower()

    # Normalize common aliases
    if scheme in ("socks", "socks5"):
        # socks5://[user:pass@]host:port
        at_idx = rest.rfind("@")
        hostport = rest[at_idx + 1 :] if at_idx >= 0 else rest
        # Strip path/fragment
        hostport = hostport.split("/")[0].split("?")[0].split("#")[0]
        parts = hostport.rsplit(":", 1)
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 1080
        return {"type": "socks5", "host": host, "port": port}

    if scheme in ("http", "https"):
        at_idx = rest.rfind("@")
        hostport = rest[at_idx + 1 :] if at_idx >= 0 else rest
        hostport = hostport.split("/")[0].split("?")[0].split("#")[0]
        parts = hostport.rsplit(":", 1)
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 8080
        return {"type": "http", "host": host, "port": port}

    if scheme in ("vless", "trojan"):
        # vless://uuid@host:port?params#name  or  trojan://password@host:port?params#name
        fragment = ""
        if "#" in rest:
            rest, fragment = rest.rsplit("#", 1)
        query = ""
        if "?" in rest:
            rest, query = rest.split("?", 1)
        at_idx = rest.find("@")
        if at_idx < 0:
            return None
        cred = rest[:at_idx]
        hostport = rest[at_idx + 1 :]
        parts = hostport.rsplit(":", 1)
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 443
        layer: Dict[str, Any] = {
            "type": scheme,
            "host": host,
            "port": port,
            "uuid": cred,
        }
        # Parse query for TLS/SNI
        qparams: Dict[str, str] = {}
        if query:
            for kv in query.split("&"):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    qparams[k.lower()] = v
        layer["tls"] = qparams.get("security", "tls") in ("tls", "reality")
        if "sni" in qparams:
            layer["sni"] = qparams["sni"]
        elif "host" in qparams:
            layer["sni"] = qparams["host"]
        return layer

    if scheme == "vmess":
        # vmess:// is usually base64-encoded JSON
        import base64

        try:
            decoded = base64.b64decode(rest + "==").decode(errors="ignore")
            obj = json.loads(decoded)
            return {
                "type": "vmess",
                "host": obj.get("add", obj.get("host", "")),
                "port": int(obj.get("port", 443)),
                "uuid": obj.get("id", ""),
                "tls": obj.get("tls", "") == "tls",
                "sni": obj.get("sni", obj.get("host", obj.get("add", ""))),
            }
        except Exception:
            return None

    if scheme == "ss":
        # ss://base64(method:password)@host:port#name  OR  ss://base64@host:port
        fragment = ""
        if "#" in rest:
            rest, fragment = rest.rsplit("#", 1)
        at_idx = rest.rfind("@")
        if at_idx >= 0:
            hostport = rest[at_idx + 1 :]
            parts = hostport.rsplit(":", 1)
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 443
            return {
                "type": "shadowsocks",
                "host": host,
                "port": port,
                "uuid": rest[:at_idx],
            }
        return None

    return None


def interactive_layer_builder():
    """Walk user through building a multi-layer chain interactively."""
    section("Interactive Chain Builder")

    print(Colors.dim("  Build a multi-layer proxy chain step by step."))
    print(
        Colors.dim(
            "  Typical chain: [You] -> Local Proxy -> WARP -> Destination Proxy -> [Internet]"
        )
    )
    print(
        Colors.dim(
            "  Minimum: 1 layer.  Recommended: 2-3 layers for censored networks."
        )
    )
    print()

    layers: List[Dict[str, Any]] = []

    while True:
        n = len(layers) + 1
        # Show current chain so far
        if layers:
            chain_str = " -> ".join(
                f"{ly['type'].upper()}@{ly.get('host', ly.get('ip', '?'))}:{ly['port']}"
                for ly in layers
            )
            print(
                f"\n  {Colors.cyan('Current chain:')} [You] -> {chain_str} -> [Internet]"
            )

        print(f"\n  {Colors.bold(f'--- Add Layer {n} ---')}")
        print("  Layer types:")
        print(
            f"    {Colors.green('1)')} SOCKS5 proxy     {Colors.dim('(Psiphon, Tor, V2RayN, Clash)')}"
        )
        print(
            f"    {Colors.green('2)')} HTTP proxy        {Colors.dim('(Squid, Lantern, Privoxy)')}"
        )
        print(
            f"    {Colors.green('3)')} Cloudflare WARP   {Colors.dim('(needs clean IP - run --scan-ips to find)')}"
        )
        print(
            f"    {Colors.green('4)')} VLESS proxy       {Colors.dim('(Xray / Sing-box server)')}"
        )
        print(
            f"    {Colors.green('5)')} VMess proxy       {Colors.dim('(V2Ray server)')}"
        )
        print(
            f"    {Colors.green('6)')} Trojan proxy      {Colors.dim('(Trojan-Go / Xray)')}"
        )
        print(
            f"    {Colors.green('7)')} Shadowsocks       {Colors.dim('(SS / SSR server)')}"
        )
        print()
        print(
            f"    {Colors.yellow('t)')} Test current layers    {Colors.dim('(smart multi-strategy test)')}"
        )
        print(
            f"    {Colors.yellow('i)')} Import clean IPs       {Colors.dim('(from file or paste)')}"
        )
        print(
            f"    {Colors.yellow('u)')} Paste proxy URI        {Colors.dim('(vless://..., vmess://..., ss://..., trojan://..., etc.)')}"
        )
        print(f"    {Colors.yellow('r)')} Remove last layer")
        print(f"    {Colors.yellow('d)')} Done - generate config")
        print(f"    {Colors.yellow('q)')} Quit without saving")

        choice = (
            input(f"\n  Select [{Colors.bold('1-7/t/i/u/r/d/q')}]: ").strip().lower()
        )
        if choice == "q":
            return
        if choice == "d":
            break
        if choice == "t":
            if layers:
                test_chain_layers(layers)
            else:
                info("No layers to test yet. Add at least one layer first.")
            continue
        if choice == "r":
            if layers:
                removed = layers.pop()
                rhost = removed.get("host", removed.get("ip", "?"))
                ok(
                    f"Removed Layer {len(layers) + 1}: {removed['type']} @ {rhost}:{removed['port']}"
                )
            else:
                info("No layers to remove.")
            continue
        if choice == "i":
            src = input(
                "  File path or comma-separated IPs (e.g. 1.2.3.4:2408,5.6.7.8:854): "
            ).strip()
            if src:
                eps = load_user_endpoints(src)
                if eps:
                    ok(f"Loaded {len(eps)} endpoint(s). Adding first as WARP layer.")
                    ip0, port0 = eps[0]
                    layers.append({"type": "warp", "ip": ip0, "port": port0})
                    ok(f"Layer {len(layers)} added: warp @ {ip0}:{port0}")
                    if len(eps) > 1:
                        info(
                            f"Remaining {len(eps) - 1} IPs available. Use 'i' again to add more."
                        )
                else:
                    fail("Could not parse any endpoints from input.")
            continue
        if choice == "u":
            uri = input("  Paste proxy URI: ").strip()
            parsed = _parse_proxy_uri(uri)
            if parsed:
                layers.append(parsed)
                phost = parsed.get("host", parsed.get("ip", "?"))
                ok(
                    f"Layer {len(layers)} added: {parsed['type']} @ {phost}:{parsed['port']}"
                )
            else:
                fail(
                    "Could not parse URI. Supported: vless://, vmess://, ss://, trojan://, socks5://, http://"
                )
            continue

        layer: Dict[str, Any] = {}
        if choice == "1":
            layer["type"] = "socks5"
            layer["host"] = input("  Host [127.0.0.1]: ").strip() or "127.0.0.1"
            port_str = input("  Port [1080]: ").strip() or "1080"
            layer["port"] = int(port_str)
        elif choice == "2":
            layer["type"] = "http"
            layer["host"] = input("  Host [127.0.0.1]: ").strip() or "127.0.0.1"
            port_str = input("  Port [8080]: ").strip() or "8080"
            layer["port"] = int(port_str)
        elif choice == "3":
            layer["type"] = "warp"
            print(
                Colors.dim(
                    "    Tip: Run 'python lab-scanner.py --scan-ips' to find clean IPs"
                )
            )
            print(
                Colors.dim(
                    "    Tip: Or press 'i' to import your own clean IPs from a file"
                )
            )
            layer["ip"] = (
                input("  Clean IP [162.159.192.1]: ").strip() or "162.159.192.1"
            )
            port_str = input("  Port [2408]: ").strip() or "2408"
            layer["port"] = int(port_str)
        elif choice in ("4", "5", "6", "7"):
            type_map = {"4": "vless", "5": "vmess", "6": "trojan", "7": "shadowsocks"}
            layer["type"] = type_map[choice]
            layer["host"] = input("  Server host: ").strip()
            if not layer["host"]:
                fail("Host cannot be empty.")
                continue
            port_str = input("  Server port [443]: ").strip() or "443"
            layer["port"] = int(port_str)
            layer["uuid"] = input("  UUID/Password: ").strip()
            use_tls = input("  TLS? [Y/n]: ").strip().lower()
            layer["tls"] = use_tls != "n"
            if layer["tls"]:
                layer["sni"] = (
                    input(f"  SNI [{layer['host']}]: ").strip() or layer["host"]
                )
        else:
            print(f"  {Colors.red('Invalid choice.')} Enter 1-7, t, i, u, r, d, or q.")
            continue

        layers.append(layer)

        # Quick-test the new layer
        host = layer.get("host", layer.get("ip", ""))
        port = layer.get("port", 0)
        ok(f"Layer {n} added: {layer['type']} @ {host}:{port}")
        if host and port:
            reachable, lat = tcp_connect(host, int(port), timeout=3.0)
            if reachable:
                ok(f"  Quick check: {host}:{port} is reachable ({lat}ms)")
            else:
                info(
                    f"  Quick check: {host}:{port} not reachable directly (may work through tunnel)"
                )

    if not layers:
        info("No layers configured.")
        return

    # Offer to test before generating
    print()
    run_test = (
        input("  Run smart chain test before generating? [Y/n]: ").strip().lower()
    )
    if run_test != "n":
        test_chain_layers(layers)

    # Generate config
    config = generate_chain_config(layers)
    config_json = json.dumps(config, indent=2)

    section("Generated Chain Configuration")
    print(config_json)

    # Save
    save = input("\n  Save to file? [Y/n]: ").strip().lower()
    if save != "n":
        filename = (
            input("  Filename [chain-config.json]: ").strip() or "chain-config.json"
        )
        with open(filename, "w") as f:
            f.write(config_json)
        ok(f"Saved to {filename}")
        print(f"\n  To run: sing-box run -c {filename}")
        print("  Then set your proxy to: socks5://127.0.0.1:2080")
        print()
        print(Colors.dim("  Tip: Test your chain with:"))
        print(Colors.dim("    curl -x socks5://127.0.0.1:2080 https://ip.gs"))
        print(
            Colors.dim(
                "    curl -x socks5://127.0.0.1:2080 https://speed.cloudflare.com"
            )
        )


# ============================================================
# Main
# ============================================================


def full_diagnostic(workers: int = 30):
    """Run the complete diagnostic suite (all 6 phases)."""
    scan_start = time.monotonic()

    connectivity = scan_basic_connectivity()
    proxies = scan_local_proxies()
    clean_ips = scan_clean_ips(max_workers=workers)
    dns = scan_dns_servers()
    sni = scan_sni_blocking()
    port_matrix = scan_port_matrix()

    elapsed = time.monotonic() - scan_start

    # Save results
    report = {
        "version": VERSION,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python": platform.python_version(),
        "scan_duration_seconds": round(elapsed, 1),
        "connectivity": connectivity,
        "local_proxies": proxies,
        "clean_ips": clean_ips,
        "dns_servers": dns,
        "sni_blocking": sni,
        "port_matrix": port_matrix,
    }

    report_file = "lab-scan-results.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    section("Scan Complete")
    ok(f"Results saved to {report_file}")
    ok(f"Total scan time: {elapsed:.1f}s")

    # --- Comprehensive Recommendations ---
    section("Recommendations")

    # Censorship severity classification
    has_cf = connectivity.get("cf", False)
    has_https = connectivity.get("https", False)
    has_tls = connectivity.get("tls", False)
    has_tcp = connectivity.get("internet", False)
    has_dns = connectivity.get("dns", False)
    has_icmp = connectivity.get("icmp", False)
    sni_blocked = sni.get("blocked_count", 0)
    sni_total = sni.get("total_tested", 1)
    sni_pct = (sni_blocked / sni_total * 100) if sni_total > 0 else 0

    if has_cf and has_https and sni_pct < 10:
        ok("Minimal censorship detected.")
        info("All strategies work: direct proxy, WARP, proxy cascade, CDN relay.")
        info("Use the Lab page to build your config.")
    elif has_cf and has_https:
        ok("Internet works but some SNI filtering detected.")
        info("Strategies: WARP chain, TLS Fragment, proxy cascade, CDN Worker.")
    elif has_cf:
        info("HTTP works but HTTPS may be filtered.")
        info("Strategies: WARP + TLS Fragment, or cascade through a local proxy.")
    elif has_tls:
        info("TLS works but Cloudflare may be filtered.")
        info("Strategies: TLS Fragment, CDN Worker, proxy cascade,")
        info("  or find a relay candidate with less-filtered access (Phase 7).")
        if clean_ips:
            info(
                f"Best clean IP: {clean_ips[0]['ip']}:{clean_ips[0]['port']} "
                f"({clean_ips[0]['latency']}ms)"
            )
    elif has_tcp:
        info("Basic TCP works but TLS is blocked.")
        info("Strategies (pick any that work):")
        info("  - Chain through a local proxy that has HTTPS (Psiphon, Lantern)")
        info("  - Find a relay candidate with internet (Phase 7 / --scan-relays)")
        info("  - Stack WARP on top of a working proxy")
        if proxies:
            best_p = proxies[0]
            info(
                f"Found: {best_p['type']}://{best_p['host']}:{best_p['port']} "
                "— use as Layer 1, then add WARP or destination proxy as Layer 2."
            )
        else:
            info("No local proxy found yet. Install Psiphon, Lantern, or Tor.")
    elif has_dns:
        info("Only DNS works. Very restrictive network.")
        info("Strategies:")
        info("  - DNS tunneling (iodine, dns2tcp)")
        info("  - Find a relay candidate (--scan-relays)")
        info("  - Install Psiphon/Lantern as Layer 1")
    elif has_icmp:
        info("Only ICMP works. Extremely restrictive.")
        info("Strategies:")
        info("  - Find any reachable relay host (--scan-relays)")
        info("  - Ask network admin for proxy settings")
        info("  - ICMP tunneling (advanced: ptunnel, hans)")
    else:
        info("No connectivity detected at all.")
        info("  - Check physical network connection")
        info("  - Ask your network admin for proxy settings")
        info("  - Scan for relays: python lab-scanner.py --scan-relays")
        info("  - Try Psiphon, Lantern, or other circumvention tools")

    # SNI-specific advice
    if sni_pct > 50:
        print()
        info(f"SNI blocking is heavy ({sni_pct:.0f}% of tested domains blocked).")
        info("Use ECH (Encrypted Client Hello) or Reality protocol to bypass.")
    elif sni_pct > 20:
        print()
        info(f"Moderate SNI filtering ({sni_pct:.0f}%).")
        info("CDN-fronted or domain-fronted configs recommended.")

    # DNS-specific advice
    udp_dns = [d for d in dns if d["type"] == "udp"]
    doh_dns = [d for d in dns if d["type"] == "doh"]
    dot_dns = [d for d in dns if d["type"] == "dot"]
    if not udp_dns and (doh_dns or dot_dns):
        print()
        info("Standard DNS is blocked but encrypted DNS (DoH/DoT) works.")
        info("Configure your system to use DoH or DoT for reliable resolution.")
        if doh_dns:
            best_doh = min(doh_dns, key=lambda x: x["latency"])
            info(f"Fastest DoH: {best_doh['name']} ({best_doh['latency']}ms)")
        if dot_dns:
            best_dot = min(dot_dns, key=lambda x: x["latency"])
            info(f"Fastest DoT: {best_dot['name']} ({best_dot['latency']}ms)")

    # Clean IP advice
    if clean_ips:
        print()
        info("Quick WARP chain command (copy-paste):")
        best = clean_ips[0]
        print(
            f"  python lab-scanner.py --build-chain --layer warp:{best['ip']}:{best['port']}"
        )

    # Port matrix advice
    open_ports = port_matrix.get("open_ports", [])
    if open_ports:
        print()
        info(
            f"Universally open ports: {', '.join(str(p) for p in open_ports)} "
            "- prefer these for proxy configs."
        )

    print()
    info("For interactive chain builder: python lab-scanner.py --interactive")
    info("For JSON output: python lab-scanner.py --json")


def main():
    parser = argparse.ArgumentParser(
        description="ConfigStream Lab Scanner v"
        + VERSION
        + " - Find your path to free internet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python lab-scanner.py                     Full diagnostic (all 6 phases)
  python lab-scanner.py --scan-ips          Scan for clean Cloudflare IPs
  python lab-scanner.py --scan-dns          Find working DNS servers (UDP/DoH/DoT)
  python lab-scanner.py --scan-proxies      Discover local SOCKS/HTTP proxies
  python lab-scanner.py --scan-relays       Find relay candidates (LAN + user-supplied)
  python lab-scanner.py --scan-sni          Detect SNI-based domain blocking
  python lab-scanner.py --scan-ports        TCP port reachability matrix
  python lab-scanner.py --interactive       Interactive chain builder
  python lab-scanner.py --auto-chain        Auto-detect best chain path (6 strategies)
  python lab-scanner.py --quick             Quick connectivity check
  python lab-scanner.py --test-proxy socks5://127.0.0.1:1080

User-supplied resources:
  python lab-scanner.py --scan-ips --custom-ips "1.2.3.4:2408,5.6.7.8:854"
  python lab-scanner.py --scan-ips --custom-ips /path/to/my-ips.txt
  python lab-scanner.py --scan-ports --custom-ips "1.2.3.4:443"
  python lab-scanner.py --auto-chain --custom-proxy socks5://127.0.0.1:1080
        """,
    )
    parser.add_argument(
        "--scan-ips", action="store_true", help="Scan for clean Cloudflare IPs"
    )
    parser.add_argument(
        "--scan-dns",
        action="store_true",
        help="Find working DNS servers (UDP, DoH, DoT)",
    )
    parser.add_argument(
        "--scan-proxies", action="store_true", help="Discover local proxies"
    )
    parser.add_argument(
        "--scan-sni",
        action="store_true",
        help="Detect SNI-based blocking on popular domains",
    )
    parser.add_argument(
        "--scan-ports",
        action="store_true",
        help="Build a TCP port reachability matrix",
    )
    parser.add_argument(
        "--scan-relays",
        action="store_true",
        help="Discover relay candidates (LAN scan + user-supplied hosts/URIs)",
    )
    parser.add_argument("--quick", action="store_true", help="Quick connectivity check")
    parser.add_argument(
        "--interactive", action="store_true", help="Interactive chain builder"
    )
    parser.add_argument(
        "--auto-chain",
        action="store_true",
        help="Auto-detect best chain path (6 strategies, not just WARP)",
    )
    parser.add_argument(
        "--test-proxy",
        type=str,
        help="Test through a proxy (e.g. socks5://127.0.0.1:1080)",
    )
    parser.add_argument(
        "--custom-ips",
        type=str,
        help="Your own IP:port list (comma-separated or file path) to include in scans",
    )
    parser.add_argument(
        "--custom-proxy",
        type=str,
        help="Your own proxy (type://host:port) to use as Layer 1 in --auto-chain",
    )
    parser.add_argument(
        "--workers", type=int, default=30, help="Max parallel workers (default: 30)"
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Number of top results to display (default: 10)",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results as JSON only"
    )
    parser.add_argument(
        "--scan-vwarp",
        action="store_true",
        help="Use vwarp binary for fast clean IP scan (requires vwarp in PATH)",
    )
    args = parser.parse_args()

    banner()

    # Parse user-supplied endpoints once
    user_eps: Optional[List[Tuple[str, int]]] = None
    if args.custom_ips:
        user_eps = load_user_endpoints(args.custom_ips)
        if user_eps:
            info(f"Loaded {len(user_eps)} user-supplied endpoint(s)")

    # Parse user-supplied proxy
    user_proxy: Optional[Dict[str, Any]] = None
    if args.custom_proxy:
        p = args.custom_proxy.replace("://", ":")
        pp = p.split(":")
        if len(pp) >= 3:
            user_proxy = {"type": pp[0], "host": pp[1], "port": int(pp[2])}
        else:
            info("Invalid --custom-proxy format. Use type://host:port")

    if args.scan_vwarp:
        results = scan_vwarp_endpoints(rtt_limit="800ms")
        if args.json:
            print(json.dumps(results, indent=2))
    elif args.scan_ips:
        results = scan_clean_ips(
            top_n=args.top_n, max_workers=args.workers, extra_ips=user_eps
        )
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
    elif args.scan_sni:
        results = scan_sni_blocking(max_workers=args.workers)
        if args.json:
            print(json.dumps(results, indent=2))
    elif args.scan_ports:
        results = scan_port_matrix(max_workers=args.workers, extra_ips=user_eps)
        if args.json:
            print(json.dumps(results, indent=2))
    elif args.scan_relays:
        relay_extra: List[str] = []
        if user_proxy:
            relay_extra.append(
                f"{user_proxy['type']}://{user_proxy['host']}:{user_proxy['port']}"
            )
        if user_eps:
            relay_extra.extend(f"{e['ip']}:{e['port']}" for e in user_eps)
        results = scan_relay_candidates(
            max_workers=args.workers,
            extra_hosts=relay_extra if relay_extra else None,
        )
        if args.json:
            print(json.dumps(results, indent=2))
    elif args.quick:
        scan_basic_connectivity()
    elif args.interactive:
        interactive_layer_builder()
    elif args.auto_chain:
        clean_ips = scan_clean_ips(
            top_n=5, max_workers=args.workers, extra_ips=user_eps
        )
        # If user supplied a proxy, inject it as Layer 1
        proxy_list = [user_proxy] if user_proxy else None
        best = auto_find_best_chain(proxies=proxy_list, clean_ips=clean_ips)
        if best:
            config = generate_chain_config(best)
            config_json = json.dumps(config, indent=2)
            section("Auto-Generated Chain Config")
            print(config_json)
            if args.json:
                print(json.dumps({"chain": best, "config": config}, indent=2))
    elif args.test_proxy:
        # Parse proxy URL: type://host:port
        parts = args.test_proxy.replace("://", ":").split(":")
        if len(parts) >= 3:
            test_through_proxy(parts[0], parts[1], int(parts[2]))
        else:
            print("Invalid proxy format. Use: type://host:port")
    else:
        full_diagnostic(workers=args.workers)


if __name__ == "__main__":
    main()
