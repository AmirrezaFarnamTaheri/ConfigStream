"""
Output Generation Module.
Produces client-compatible configuration files and statistical reports.
"""

import json
import base64
import gzip
import logging
import os
import random
from pathlib import Path
from typing import List, Dict, Union, Optional, Any
from datetime import datetime, timezone

# Fix imports
try:
    import yaml as yaml_lib
except ImportError:
    yaml_lib = None  # type: ignore

from .models import Proxy
from .serialize import serialize_proxy

logger = logging.getLogger(__name__)


# --- Helper Functions for Clash/Singbox ---


def _safe_int_conversion(value: Any, default: int = 0) -> int:
    """
    Safely convert a value to int, handling bytes and other types.

    Args:
        value: The value to convert (can be int, str, bytes, or other)
        default: The default value if conversion fails

    Returns:
        int: The converted value or default if conversion fails
    """
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, bytes):
        # First, try to decode as UTF-8 string (handles b"2" -> "2" -> 2)
        try:
            return int(value.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            # Fall back to raw bytes interpretation only if decode fails
            try:
                return int.from_bytes(value, byteorder="big", signed=False)
            except (ValueError, OverflowError):
                return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def to_clash_proxy(proxy: Proxy) -> Optional[Dict[str, Any]]:
    """Convert internal Proxy model to Clash dictionary."""

    def _add_transport_opts(
        base: Dict[str, Any], details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Helper to add ws/grpc/http options to Clash config."""
        net = details.get("net") or details.get("type") or "tcp"
        base["network"] = net

        if net == "ws":
            ws_opts: Dict[str, Any] = {}
            if "path" in details:
                ws_opts["path"] = str(details["path"])
            if "host" in details or "sni" in details:
                ws_opts["headers"] = {
                    "Host": str(details.get("host") or details.get("sni"))
                }
            if ws_opts:
                base["ws-opts"] = ws_opts

        elif net == "grpc":
            grpc_opts: Dict[str, Any] = {}
            if "serviceName" in details:
                grpc_opts["grpc-service-name"] = str(details["serviceName"])
            if grpc_opts:
                base["grpc-opts"] = grpc_opts

        elif net == "h2" or net == "http":
            h2_opts: Dict[str, Any] = {}
            if "path" in details:
                h2_opts["path"] = [str(details["path"])]
            if "host" in details:
                h2_opts["host"] = [str(details["host"])]
            if h2_opts:
                base["h2-opts"] = h2_opts

        # Common TLS fields
        if details.get("tls") == "tls" or details.get("security") in ["tls", "reality"]:
            base["tls"] = True
            if "sni" in details:
                base["servername"] = str(details["sni"])
            if "fp" in details:
                base["client-fingerprint"] = str(details["fp"])
            if details.get("security") == "reality":
                base["client-fingerprint"] = str(
                    details.get("fp", "chrome")
                )  # Reality needs explicit FP often
                base["reality-opts"] = {
                    "public-key": str(details.get("pbk")),
                    "short-id": str(details.get("sid", "")),
                }

        return base

    base: Dict[str, Any] = {}

    if proxy.protocol == "vmess":
        base = {
            "type": "vmess",
            "server": proxy.address,
            "port": proxy.port,
            "uuid": proxy.uuid,
            "alterId": _safe_int_conversion(proxy.details.get("aid"), 0),
            "cipher": str(proxy.details.get("scy", "auto")),
        }
        return _add_transport_opts(base, proxy.details)

    elif proxy.protocol == "vless":
        base = {
            "type": "vless",
            "server": proxy.address,
            "port": proxy.port,
            "uuid": proxy.uuid,
            "flow": str(proxy.details.get("flow", "")),
        }
        return _add_transport_opts(base, proxy.details)

    elif proxy.protocol == "shadowsocks":
        return {
            "type": "ss",
            "server": proxy.address,
            "port": proxy.port,
            "cipher": str(proxy.details.get("method", "chacha20-ietf-poly1305")),
            "password": str(proxy.details.get("password", "")),
        }
    elif proxy.protocol == "trojan":
        return {
            "type": "trojan",
            "server": proxy.address,
            "port": proxy.port,
            "password": proxy.uuid,
            "udp": True,
        }
    elif proxy.protocol == "http":
        return {
            "type": "http",
            "server": proxy.address,
            "port": proxy.port,
            "username": proxy.uuid if proxy.uuid else None,
            "password": (
                str(proxy.details.get("password", ""))
                if proxy.details.get("password")
                else None
            ),
            "tls": proxy.details.get("tls") == "tls",
        }
    elif proxy.protocol == "socks5":
        return {
            "type": "socks5",
            "server": proxy.address,
            "port": proxy.port,
            "username": proxy.uuid if proxy.uuid else None,
            "password": (
                str(proxy.details.get("password", ""))
                if proxy.details.get("password")
                else None
            ),
            "tls": proxy.details.get("tls") == "tls",
        }
    elif proxy.protocol == "wireguard":
        return {
            "type": "wireguard",
            "server": proxy.address,
            "port": proxy.port,
            "ip": str(proxy.details.get("local_address", "10.10.0.2")),
            "private-key": str(proxy.details.get("private_key")),
            "public-key": str(proxy.details.get("peer_public_key")),
            "udp": True,
        }

    # Add other protocols as needed
    return None


def to_singbox_outbound(proxy: Proxy) -> Optional[Dict[str, Any]]:
    """Convert internal Proxy model to Sing-box outbound."""
    base: Dict[str, Any] = {
        "server": proxy.address,
        "server_port": proxy.port,
    }

    def _add_transport_sb(
        out: Dict[str, Any], details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Helper to add transport options for Sing-box."""
        net = details.get("net") or details.get("type") or "tcp"

        transport: Dict[str, Any] = {}
        if net == "ws":
            transport["type"] = "ws"
            if "path" in details:
                transport["path"] = str(details["path"])
            if "host" in details or "sni" in details:
                transport["headers"] = {
                    "Host": str(details.get("host") or details.get("sni"))
                }
        elif net == "grpc":
            transport["type"] = "grpc"
            if "serviceName" in details:
                transport["service_name"] = str(details["serviceName"])
        elif net == "http" or net == "h2":
            transport["type"] = "http"
            if "path" in details:
                transport["path"] = str(details["path"])
            if "host" in details:
                transport["host"] = [str(details["host"])]

        if transport:
            out["transport"] = transport

        # TLS
        if details.get("tls") == "tls" or details.get("security") in ["tls", "reality"]:
            tls: Dict[str, Any] = {"enabled": True}
            if "sni" in details:
                tls["server_name"] = str(details["sni"])
            if "fp" in details:
                tls["utls"] = {"enabled": True, "fingerprint": str(details["fp"])}

            if details.get("security") == "reality":
                tls["reality"] = {
                    "enabled": True,
                    "public_key": str(details.get("pbk")),
                    "short_id": str(details.get("sid", "")),
                }

            out["tls"] = tls

        return out

    if proxy.protocol == "vmess":
        out = {
            "type": "vmess",
            **base,
            "uuid": proxy.uuid,
            "security": "auto",
            "alter_id": _safe_int_conversion(proxy.details.get("aid"), 0),
        }
        return _add_transport_sb(out, proxy.details)

    elif proxy.protocol == "vless":
        out = {
            "type": "vless",
            **base,
            "uuid": proxy.uuid,
            "flow": str(proxy.details.get("flow", "")),
        }
        return _add_transport_sb(out, proxy.details)

    elif proxy.protocol == "shadowsocks":
        return {
            "type": "shadowsocks",
            **base,
            "method": str(proxy.details.get("method", "chacha20-ietf-poly1305")),
            "password": str(proxy.details.get("password", "")),
        }
    elif proxy.protocol == "trojan":
        return {"type": "trojan", **base, "password": proxy.uuid}

    elif proxy.protocol == "http":
        return {
            "type": "http",
            **base,
            "username": proxy.uuid if proxy.uuid else "",
            "password": str(proxy.details.get("password", "")),
            "tls": {"enabled": proxy.details.get("tls") == "tls"},
        }
    elif proxy.protocol == "socks5":
        return {
            "type": "socks",
            **base,
            "username": proxy.uuid if proxy.uuid else "",
            "password": str(proxy.details.get("password", "")),
        }
    elif proxy.protocol == "wireguard":
        return {
            "type": "wireguard",
            **base,
            "local_address": [str(proxy.details.get("local_address", "10.10.0.2/32"))],
            "private_key": str(proxy.details.get("private_key")),
            "peer_public_key": str(proxy.details.get("peer_public_key", "")),
        }
    elif proxy.protocol == "hysteria2":
        out = {
            "type": "hysteria2",
            **base,
            "password": proxy.uuid or str(proxy.details.get("password", "")),
        }
        # Add TLS
        out["tls"] = {
            "enabled": True,
            "server_name": str(proxy.details.get("sni", "")),
            "insecure": bool(proxy.details.get("allowInsecure", False)),
            "alpn": proxy.details.get("alpn", [])
        }
        # Obfs
        if proxy.details.get("obfs-type") == "salamander":
             out["obfs"] = {"type": "salamander", "password": str(proxy.details.get("obfs-password", ""))}
        return out

    elif proxy.protocol == "tuic":
        out = {
            "type": "tuic",
            **base,
            "uuid": proxy.uuid,
            "password": str(proxy.details.get("password", "")),
            "congestion_controller": str(proxy.details.get("congestion_controller", "bbr")),
        }
        # Add TLS
        out["tls"] = {
            "enabled": True,
            "server_name": str(proxy.details.get("sni", "")),
            "alpn": proxy.details.get("alpn", [])
        }
        return out

    return None


def wash_dirty_proxies(proxies: List[Proxy]) -> List[Dict[str, Any]]:
    """
    Recycles insecure proxies by chaining them to secure endpoints.
    """
    washed_outbounds = []

    # 1. Identify The "Dirty Laundry" (Insecure Proxies)
    # Must be working, but marked insecure or dirty
    dirty_socks = [
        p for p in proxies
        if p.is_working and (
            "socks" in p.protocol.lower() and ("dirty_ip" in p.tags or "insecure" in p.tags or p.protocol.lower() in ["socks", "socks5"])
        ) and ("tls" not in p.details or p.details["tls"] != "tls")
    ]
    dirty_http = [
        p for p in proxies
        if p.is_working and (
            "http" in p.protocol.lower() and ("dirty_ip" in p.tags or "insecure" in p.tags or p.protocol.lower() == "http")
        ) and ("tls" not in p.details or p.details["tls"] != "tls")
    ]

    # Also include those explicitly tagged "dirty_ip" regardless of protocol, if we can use them as relays
    # But currently we focus on SOCKS/HTTP as relays because they are simple to chain

    # 2. Identify The "Soap" (Secure Exits)
    # WARP Keys for SOCKS
    warp_keys_str = os.getenv("WARP_KEY_POOL", "[]")
    try:
        warp_keys = json.loads(warp_keys_str)
    except json.JSONDecodeError:
        warp_keys = []

    # Secure TLS Proxies for HTTP (VLESS/Trojan with TLS)
    secure_exits = [
        p for p in proxies
        if p.is_working and p.is_secure and p.protocol.lower() in ['vless', 'trojan', 'vmess']
        and (p.details.get("tls") == "tls" or p.details.get("security") in ["tls", "reality"])
    ]

    # --- CYCLE 1: WASH SOCKS5 WITH WARP ---
    if warp_keys:
        for i, socks in enumerate(dirty_socks):
            key = random.choice(warp_keys)
            if not isinstance(key, dict) or "private_key" not in key:
                continue

            # Create SOCKS outbound
            relay_out = to_singbox_outbound(socks)
            if not relay_out: continue

            relay_tag = f"WASH-SOCKS-{i}-{socks.country_code}"
            relay_out["tag"] = relay_tag

            # Create WARP Exit
            exit_tag = f"CLEAN-WARP-{i}-{socks.country_code}"
            warp_out = {
                "type": "wireguard",
                "tag": exit_tag,
                "local_address": ["172.16.0.2/32"],
                "private_key": key["private_key"],
                "peer_public_key": key.get("peer_public_key", "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo="),
                "server": "162.159.192.1",
                "server_port": 2408,
                "detour": relay_tag  # <--- The Wash
            }
            washed_outbounds.append(relay_out)
            washed_outbounds.append(warp_out)

    # --- CYCLE 2: WASH HTTP WITH TLS PROXIES ---
    if secure_exits:
        # We limit to a reasonable number to avoid exploding config size
        limit = min(len(dirty_http), 200)
        for i, http in enumerate(dirty_http[:limit]):
            # Pick a random secure exit to upgrade to
            secure_node = random.choice(secure_exits)

            # Create HTTP Relay
            relay_out = to_singbox_outbound(http)
            if not relay_out: continue

            relay_tag = f"WASH-HTTP-{i}-{http.country_code}"
            relay_out["tag"] = relay_tag

            # Create Secure Exit (Modified to detour through HTTP)
            exit_out = to_singbox_outbound(secure_node)
            if not exit_out: continue

            exit_tag = f"CLEAN-TLS-{i}-{secure_node.country_code}-via-{http.country_code}"
            exit_out["tag"] = exit_tag
            exit_out["detour"] = relay_tag # <--- The Upgrade

            washed_outbounds.append(relay_out)
            washed_outbounds.append(exit_out)

    return washed_outbounds


def generate_exotic_chains(proxies: List[Proxy]) -> List[Dict[str, Any]]:
    """
    Generate exotic proxy chains (Double-Hop) to solve censorship challenges.
    """
    chains = []

    # 1. Categorize Proxies
    # Relays: Good at bypass (Hysteria, Reality, Tuic)
    relays = [
        p for p in proxies
        if p.is_working and (
            p.protocol.lower() in ['hysteria2', 'tuic'] or
            p.details.get('security') == 'reality'
        )
    ]

    # Exits: Standard protocols (VMess, SS, Trojan)
    exits = [
        p for p in proxies
        if p.is_working and p.protocol.lower() in ['vmess', 'shadowsocks', 'trojan']
    ]

    # 2. Generate Pairs (Create 20 random chains)
    if not relays or not exits:
        return chains

    # Use a loop that doesn't depend on min(len) being restrictive if we reuse relays
    # But we want max 20 chains
    # Using max(1, ...) ensures target_count is at least 1 if relays/exits exist,
    # but we cap at 20. The previous logic min(len) limited us to the smallest pool size.
    # We want to allow reusing relays/exits.
    target_count = min(20, max(len(relays), len(exits)) * 2) # Heuristic to try getting 20
    target_count = min(20, target_count)
    target_count = max(1, target_count) # Ensure at least 1 loop if lists are small but non-empty

    for i in range(target_count):
        relay_node = random.choice(relays)
        exit_node = random.choice(exits)

        # Convert to Sing-box Objects
        relay_out = to_singbox_outbound(relay_node)
        exit_out = to_singbox_outbound(exit_node)

        if not relay_out or not exit_out:
            continue

        # 3. The Magic: Link them via Tags
        relay_tag = f"RELAY-{i}-{relay_node.country_code}"
        relay_out["tag"] = relay_tag

        exit_tag = f"CHAIN-{i}-{relay_node.country_code}-to-{exit_node.country_code}"
        exit_out["tag"] = exit_tag

        # This line creates the tunnel: Exit traffic flows THROUGH Relay
        exit_out["detour"] = relay_tag

        chains.append(relay_out)
        chains.append(exit_out)

    return chains


def generate_split_outputs(proxies: List[Proxy], output_dir: Path, washed_outbounds: List[Dict[str, Any]]) -> Dict[str, Path]:
    """
    Generate specific configuration files for different use cases.
    Includes washed proxies in Sing-box configs.
    """
    files: Dict[str, Path] = {}

    # 1. singbox-vpn.json (The "Tank") - Tun, GVisor, FakeIP
    # Include normal proxies + washed proxies (only the exits of the chains)
    # Filter washed outbounds for 'exits' (tags starting with CLEAN or CHAIN)
    washed_exits = [o for o in washed_outbounds if o.get("tag", "").startswith(("CLEAN-", "CHAIN-"))]
    washed_relays = [o for o in washed_outbounds if not o.get("tag", "").startswith(("CLEAN-", "CHAIN-"))]

    # We need all underlying proxies for the exits to work, so include relays too but don't add to selector
    all_sb_outbounds = []
    selector_tags = []

    # Add standard proxies
    for i, p in enumerate(proxies, 1):
        out = to_singbox_outbound(p)
        if out:
            tag = f"{p.country_code or 'XX'} {i:02d} | {p.protocol.upper()}"
            out["tag"] = tag
            all_sb_outbounds.append(out)
            selector_tags.append(tag)

    # Add washed/chained proxies
    for out in washed_exits:
        all_sb_outbounds.append(out)
        selector_tags.append(out["tag"])

    for out in washed_relays:
        all_sb_outbounds.append(out)

    # VPN Config
    vpn_config = {
        "log": {"level": "info"},
        "dns": {
            "servers": [
                {"tag": "google", "address": "8.8.8.8", "detour": "🌍 Proxy Select"},
                {"tag": "local", "address": "223.5.5.5", "detour": "direct"}
            ],
            "rules": [
                {"outbound": "any", "server": "google"}
            ],
            "final": "google",
            "strategy": "ipv4_only"
        },
        "inbounds": [
            {
                "type": "tun",
                "tag": "tun-in",
                "interface_name": "tun0",
                "inet4_address": "172.19.0.1/30",
                "auto_route": True,
                "strict_route": True,
                "stack": "gvisor",
                "sniff": True
            }
        ],
        "outbounds": [
            {
                "type": "selector",
                "tag": "🌍 Proxy Select",
                "outbounds": ["🚀 Auto"] + selector_tags
            },
            {
                "type": "urltest",
                "tag": "🚀 Auto",
                "outbounds": selector_tags,
                "url": "http://www.gstatic.com/generate_204",
                "interval": "5m"
            },
            {"type": "direct", "tag": "direct"},
            {"type": "dns", "tag": "dns-out"}
        ] + all_sb_outbounds
    }

    vpn_file = output_dir / "singbox-vpn.json"
    with open(vpn_file, "w", encoding="utf-8") as f:
        json.dump(vpn_config, f, indent=2)
    files["singbox_vpn"] = vpn_file

    # 2. singbox.json (The "Sniper") - Mixed Port, Fragment
    sniper_config = {
        "log": {"level": "info"},
        "inbounds": [
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "127.0.0.1",
                "listen_port": 2080,
                "sniff": True
            }
        ],
        "outbounds": [
            {
                "type": "selector",
                "tag": "🌍 Proxy Select",
                "outbounds": ["🚀 Auto"] + selector_tags
            },
            {
                "type": "urltest",
                "tag": "🚀 Auto",
                "outbounds": selector_tags,
                "url": "http://www.gstatic.com/generate_204",
                "interval": "5m"
            },
            {"type": "direct", "tag": "direct"},
            {"type": "dns", "tag": "dns-out"}
        ] + all_sb_outbounds
    }

    # Inject fragmentation for Sniper (as per roadmap)
    for out in sniper_config["outbounds"]:
        if "tls" in out and isinstance(out["tls"], dict):
            # Don't override if already there?
            # Add fragment
            out["tls"]["tls_fragment"] = {
                "enabled": True,
                "size": "100-200",
                "sleep": "10-20"
            }

    sniper_file = output_dir / "singbox.json"
    with open(sniper_file, "w", encoding="utf-8") as f:
        json.dump(sniper_config, f, indent=2)
    files["singbox"] = sniper_file

    # 3. clash.yaml (The "Diplomat") - Conservative, No Wash
    # Filter out experimental stuff (washed/chained) for Clash as it's legacy
    clash_content = generate_clash_config(proxies) # Uses standard proxies only
    clash_file = output_dir / "clash.yaml"
    with open(clash_file, "w", encoding="utf-8") as f:
        f.write(clash_content)
    files["clash"] = clash_file

    return files


def generate_categorized_outputs(
    proxies: List[Proxy], output_dir: Path
) -> Dict[str, Path]:
    """
    Generate files organized by protocol and country.
    """
    files: Dict[str, Path] = {}

    # 1. Master List (Standard)
    master_file = output_dir / "proxies.json"
    save_json(
        proxies, master_file, compress=True
    )  # Compress by default for large files
    files["master"] = master_file

    # 1.1 Generate Advanced (Washed & Chained) Proxies
    washed_proxies = wash_dirty_proxies(proxies)
    exotic_chains = generate_exotic_chains(proxies)
    all_advanced_outbounds = washed_proxies + exotic_chains

    # Save Chains separately (Sing-box only)
    chains_file = output_dir / "singbox-chains.json"
    with open(chains_file, "w", encoding="utf-8") as f:
        # Create a mini config for just chains
        chain_tags = [o["tag"] for o in exotic_chains if o["tag"].startswith("CHAIN-")]
        chain_config = {
            "outbounds": exotic_chains
        }
        json.dump(chain_config, f, indent=2)
    files["chains"] = chains_file

    # 2. By Protocol
    proto_dir = output_dir / "by_protocol"
    proto_dir.mkdir(exist_ok=True)

    by_proto: Dict[str, List[Proxy]] = {}
    for p in proxies:
        proto = p.protocol.lower()
        if proto not in by_proto:
            by_proto[proto] = []
        by_proto[proto].append(p)

    for proto, subset in by_proto.items():
        fpath = proto_dir / f"{proto}.json"
        save_json(subset, fpath)
        files[f"proto_{proto}"] = fpath

    # 3. By Country
    country_dir = output_dir / "by_country"
    country_dir.mkdir(exist_ok=True)

    by_country: Dict[str, List[Proxy]] = {}
    for p in proxies:
        cc = (p.country_code or "UNK").upper()
        if cc not in by_country:
            by_country[cc] = []
        by_country[cc].append(p)

    for cc, subset in by_country.items():
        fpath = country_dir / f"{cc}.json"
        save_json(subset, fpath)
        files[f"country_{cc}"] = fpath

    # 4. Generate Split Outputs (Tank, Sniper, Diplomat)
    split_files = generate_split_outputs(proxies, output_dir, all_advanced_outbounds)
    files.update(split_files)

    return files


def save_json(proxies: List[Proxy], path: Path, compress: bool = False) -> None:
    """
    Save list of proxies to JSON file atomically with fsync for durability.
    If compress=True, also saves a .gz version.
    """
    data = [serialize_proxy(p) for p in proxies]
    json_content = json.dumps(data, indent=2, ensure_ascii=False)

    # Save plain JSON atomically using temp file + fsync + rename
    temp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        # Write with fsync for crash safety
        temp_fd = os.open(str(temp_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        try:
            os.write(temp_fd, json_content.encode("utf-8"))
            os.fsync(temp_fd)  # Ensure data hits disk before rename
        finally:
            os.close(temp_fd)

        # On POSIX systems, rename is atomic. On Windows it's atomic in Python 3.3+
        temp_path.replace(path)
    except Exception:
        # Clean up temp file if something went wrong
        if temp_path.exists():
            temp_path.unlink()
        raise

    # Save Gzipped version atomically
    if compress:
        gz_path = Path(str(path) + ".gz")
        temp_gz_path = gz_path.with_suffix(gz_path.suffix + ".tmp")
        try:
            with gzip.open(temp_gz_path, "wt", encoding="utf-8") as f:
                f.write(json_content)
            temp_gz_path.replace(gz_path)
        except Exception:
            if temp_gz_path.exists():
                temp_gz_path.unlink()
            raise


def save_metadata(
    stats: Dict[str, Union[int, float]], proxies: List[Proxy], output_dir: Path
) -> None:
    """
    Save metadata.json with statistics for the frontend.
    """
    # Calculate breakdowns
    protocols: Dict[str, int] = {}
    countries: Dict[str, int] = {}
    country_stats: Dict[str, int] = {}

    # Latency buckets: <100ms, 100-500ms, 500-1000ms, >1s
    latency_distribution = {
        "fast": 0,  # < 100ms
        "medium": 0,  # 100-500ms
        "slow": 0,  # 500-1000ms
        "very_slow": 0,  # > 1000ms
    }

    for p in proxies:
        proto = p.protocol.lower()
        protocols[proto] = protocols.get(proto, 0) + 1

        cc = (p.country_code or "UNK").upper()
        countries[cc] = countries.get(cc, 0) + 1
        country_stats[cc] = country_stats.get(cc, 0) + 1

        # Use p.latency (float) which is in milliseconds
        latency = p.latency
        if latency is not None and latency > 0:
            if latency < 100:
                latency_distribution["fast"] += 1
            elif latency < 500:
                latency_distribution["medium"] += 1
            elif latency < 1000:
                latency_distribution["slow"] += 1
            else:
                latency_distribution["very_slow"] += 1
        else:
            latency_distribution["very_slow"] += 1

    # Type-safe conversion
    total_working = int(stats.get("working", 0))
    fetched_lines = int(stats.get("fetched_lines", 0))
    duration = float(stats.get("duration", 0.0))

    metadata = {
        "last_updated_utc": datetime.now(timezone.utc).isoformat(),
        "total_proxies": len(proxies),
        "total_working": total_working,
        "total_fetched": fetched_lines,
        "duration_seconds": duration,
        "protocols": protocols,
        "countries": countries,
        "country_stats": country_stats,
        "latency_distribution": latency_distribution,  # Added real data
        "protocol_colors": {
            "vmess": "#FF6B6B",
            "vless": "#4ECDC4",
            "shadowsocks": "#45B7D1",
            "trojan": "#96CEB4",
            "hysteria": "#FFEAA7",
            "hysteria2": "#DFE6E9",
            "tuic": "#A29BFE",
            "wireguard": "#74B9FF",
            "naive": "#FD79A8",
            "http": "#FDCB6E",
            "https": "#6C5CE7",
            "socks": "#00B894",
            "socks5": "#00B894",
            "openvpn": "#E84393",
        },
    }

    # Write metadata atomically with fsync
    metadata_content = json.dumps(metadata, indent=2)
    for filename in ["metadata.json", "summary.json"]:
        target_path = output_dir / filename
        temp_path = target_path.with_suffix(target_path.suffix + ".tmp")
        try:
            # Write with fsync for crash safety
            temp_fd = os.open(
                str(temp_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644
            )
            try:
                os.write(temp_fd, metadata_content.encode("utf-8"))
                os.fsync(temp_fd)
            finally:
                os.close(temp_fd)

            temp_path.replace(target_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise


def generate_clash_config(proxies: List[Proxy]) -> str:
    """Generate Clash YAML configuration."""
    if yaml_lib is None:
        return "# PyYAML not installed"

    clash_proxies = []
    names = []

    for i, p in enumerate(proxies, 1):
        # Generate a unique name
        display_name = f"{p.country_code or 'XX'} {i:02d} | {p.protocol.upper()}"

        config = to_clash_proxy(p)
        if config:
            config["name"] = display_name
            clash_proxies.append(config)
            names.append(display_name)

    payload = {
        "port": 7890,
        "socks-port": 7891,
        "allow-lan": True,
        "mode": "Rule",
        "log-level": "info",
        "external-controller": "127.0.0.1:9090",
        "proxies": clash_proxies,
        "proxy-groups": [
            {
                "name": "🚀 ConfigStream Auto",
                "type": "url-test",
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
                "tolerance": 50,
                "proxies": names,
            },
            {
                "name": "🌍 Proxy Select",
                "type": "select",
                "proxies": names + ["🚀 ConfigStream Auto"],
            },
        ],
        "rules": ["MATCH,🚀 ConfigStream Auto"],
    }

    # Ensure return is always a string
    result = yaml_lib.dump(payload, allow_unicode=True, sort_keys=False)
    return str(result) if result else ""


def generate_singbox_config(proxies: List[Proxy]) -> str:
    """Generate Sing-box JSON configuration."""
    outbounds: List[Dict[str, Any]] = []
    selector_tags: List[str] = []

    for i, p in enumerate(proxies, 1):
        config = to_singbox_outbound(p)
        if config:
            tag = f"{p.country_code or 'XX'} {i:02d} | {p.protocol.upper()}"
            config["tag"] = tag
            outbounds.append(config)
            selector_tags.append(tag)

    # Add selector and auto groups
    if selector_tags:
        outbounds.insert(
            0,
            {
                "type": "selector",
                "tag": "🌍 Proxy Select",
                "outbounds": ["🚀 Auto"] + selector_tags,
            },
        )
        outbounds.insert(
            1,
            {
                "type": "urltest",
                "tag": "🚀 Auto",
                "outbounds": selector_tags,
                "url": "http://www.gstatic.com/generate_204",
                "interval": "5m",
            },
        )

    # Basic structure
    full_config = {
        "log": {"level": "info"},
        "inbounds": [
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "127.0.0.1",
                "listen_port": 2080,
            }
        ],
        "outbounds": outbounds,
    }

    return json.dumps(full_config, indent=2)


def generate_base64_subscription(proxies: List[Proxy]) -> str:
    """Generate standard Base64 subscription string."""
    lines = []
    for p in proxies:
        if p.config:
            # Handle OpenVPN full content which isn't a one-liner usually
            if p.protocol == "openvpn":
                # For OVPN, we can't really put it in a base64 sub easily mixed with others
                # unless we encode it specifically.
                # Typically subs are list of URLs.
                # We skip OpenVPN content for the general sub list to avoid breaking clients
                continue
            if "://" in p.config:
                lines.append(p.config)

    text = "\n".join(lines)
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")
