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
import hashlib
from pathlib import Path
from typing import List, Dict, Union, Optional, Any, Set
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
    """
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, bytes):
        try:
            return int(value.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
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
                )
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
        out["tls"] = {
            "enabled": True,
            "server_name": str(proxy.details.get("sni", "")),
            "insecure": bool(proxy.details.get("allowInsecure", False)),
            "alpn": proxy.details.get("alpn", [])
        }
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
        out["tls"] = {
            "enabled": True,
            "server_name": str(proxy.details.get("sni", "")),
            "alpn": proxy.details.get("alpn", [])
        }
        return out

    return None

# --- Proxy Washer (Consistent Hashing) ---

class ProxyWasher:
    def __init__(self, warp_keys_json: str):
        try:
            self.warp_keys = json.loads(warp_keys_json) if warp_keys_json else []
        except json.JSONDecodeError:
            self.warp_keys = []
        self.seen_chains: Set[str] = set()

    def _get_consistent_exit(self, relay_id: str, exit_pool: List[Dict]) -> Optional[Dict]:
        """
        Selects an exit node deterministically based on the relay's ID.
        Acts as a 'Stateless Cache'.
        """
        if not exit_pool:
            return None

        # Create a deterministic index from the Relay ID
        hash_val = int(hashlib.md5(relay_id.encode()).hexdigest(), 16)
        index = hash_val % len(exit_pool)
        return exit_pool[index]

    def wash_batch(self, proxies: List[Proxy]) -> List[Dict[str, Any]]:
        """
        Process a batch of proxies, identifying 'washable' candidates
        and generating unique chains.
        """
        washed_outbounds = []

        # 1. Identify Candidates (Dirty or Insecure)
        candidates = [
            p for p in proxies
            if p.is_working and ("dirty_ip" in p.tags or "insecure" in p.tags)
        ]

        for i, relay in enumerate(candidates):
            # 2. Select the "Soap" (Exit Node)
            # We use our WARP pool as the default soap
            if not self.warp_keys:
                break

            exit_key = self._get_consistent_exit(relay.id, self.warp_keys)
            if not exit_key or "private_key" not in exit_key:
                continue

            # 3. Generate Deterministic Chain ID
            chain_id = f"CHAIN-{relay.country_code}-{relay.id[:6]}-{exit_key.get('id', '00')[:4]}"

            if chain_id in self.seen_chains:
                continue # Skip duplicates
            self.seen_chains.add(chain_id)

            # 4. Construct the Chain Objects
            relay_out = to_singbox_outbound(relay)
            if not relay_out: continue

            relay_tag = f"RELAY-{chain_id}"
            relay_out["tag"] = relay_tag

            exit_tag = f"🛡️ Secure-{relay.country_code}-{i+1}"
            warp_out = {
                "type": "wireguard",
                "tag": exit_tag,
                "local_address": ["172.16.0.2/32"],
                "private_key": exit_key["private_key"],
                "server": "162.159.192.1",
                "server_port": 2408,
                "peer_public_key": exit_key.get("peer_public_key", "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo="),
                "detour": relay_tag  # <--- The Link
            }

            washed_outbounds.append(relay_out)
            washed_outbounds.append(warp_out)

        return washed_outbounds


def create_chain(relay: Proxy, exit_node: Proxy, tag_prefix: str) -> List[Dict[str, Any]]:
    """Helper to generate Sing-box outbound objects for a chain."""
    relay_out = to_singbox_outbound(relay)
    exit_out = to_singbox_outbound(exit_node)

    if not relay_out or not exit_out:
        return []

    relay_tag = f"{tag_prefix}-RELAY-{relay.id[:6]}"
    exit_tag = f"{tag_prefix}-EXIT-{exit_node.country}-{exit_node.id[:6]}"

    relay_out["tag"] = relay_tag
    exit_out["tag"] = exit_tag
    exit_out["detour"] = relay_tag # The chaining magic

    return [relay_out, exit_out]


def generate_smart_chains(proxies: List[Proxy]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate intelligent proxy chains based on network topology.
    Returns a dict of chain types to list of outbound objects.
    """
    chains: Dict[str, List[Dict[str, Any]]] = {
        "intranet": [],
        "ipv6": [],
        "streamer": [],
        "experimental": [] # Hysteria->VMess
    }

    # 1. Categorize Resources
    relays_ir = [p for p in proxies if p.country_code == "IR" and p.is_working]
    relays_dual_stack = [p for p in proxies if p.is_working and ":" not in p.address] # Approx IPv4
    relays_fast = [p for p in proxies if p.is_working and p.protocol in ['hysteria2', 'tuic']]

    exits_ipv6 = [p for p in proxies if p.is_working and ":" in p.address]
    exits_streaming = [p for p in proxies if p.is_working and p.country_code in ['US', 'GB', 'DE']]
    exits_standard = [p for p in proxies if p.is_working and p.protocol in ['vmess', 'shadowsocks', 'trojan']]

    # --- CHAIN 1: THE INTRANET BRIDGE (Gold Standard) ---
    for relay in relays_ir:
        # Link to top 5 fastest foreign exits
        for exit_node in proxies[:5]:
            if exit_node.country_code != "IR" and exit_node.is_working:
                chain_objs = create_chain(relay, exit_node, "INTRANET-BRIDGE")
                if chain_objs:
                    chains["intranet"].extend(chain_objs)

    # --- CHAIN 2: THE IPv6 PORTAL ---
    for exit_node in exits_ipv6[:20]: # Limit to avoid bloat
        if relays_dual_stack:
            relay = random.choice(relays_dual_stack)
            chain_objs = create_chain(relay, exit_node, "IPv6-GATEWAY")
            if chain_objs:
                chains["ipv6"].extend(chain_objs)

    # --- CHAIN 3: THE STREAMER ---
    for exit_node in exits_streaming[:20]:
        if relays_fast:
            relay = random.choice(relays_fast)
            chain_objs = create_chain(relay, exit_node, "STREAMING-ACCEL")
            if chain_objs:
                chains["streamer"].extend(chain_objs)

    # --- CHAIN 4: EXPERIMENTAL (Hysteria -> VMess) ---
    if relays_fast and exits_standard:
        for i in range(10):
            relay = random.choice(relays_fast)
            exit_node = random.choice(exits_standard)
            chain_objs = create_chain(relay, exit_node, f"EXP-{i}")
            if chain_objs:
                chains["experimental"].extend(chain_objs)

    return chains


def generate_split_outputs(
    proxies: List[Proxy],
    output_dir: Path,
    washed_outbounds: List[Dict[str, Any]],
    smart_chains: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Path]:
    """
    Generate specific configuration files for different use cases.
    Includes washed proxies and smart chains in Sing-box configs.
    """
    files: Dict[str, Path] = {}

    # Washed Proxies (Tags starting with 🛡️ Secure)
    washed_exits = [
        o for o in washed_outbounds if o.get("tag", "").startswith("🛡️ Secure")
    ]
    # Identify original relays that were washed to exclude them from standard set (Dirty Pollution Fix)
    # washed_outbounds contains RELAY- and Secure- tags.
    # The RELAY tag format: RELAY-CHAIN-{cc}-{relay_id_prefix}-{exit_id}
    # We can't easily extract exact ID. But we can check tags.
    # Wait, washed_outbounds are the *new* outbounds.
    # The issue is that 'proxies' list still contains the dirty proxy.
    # We need to map washed chains back to original proxies if possible, OR just rely on tags?
    # Actually, ProxyWasher implementation uses `relay.id[:6]` in chain_id.
    # Let's extract those IDs from washed_outbounds RELAY tags.
    washed_relay_ids = set()
    for o in washed_outbounds:
        tag = o.get("tag", "")
        if tag.startswith("RELAY-CHAIN-"):
            # RELAY-CHAIN-IR-123456-ABCD
            parts = tag.split("-")
            if len(parts) >= 4:
                # The relay ID prefix is at index 3 (0=RELAY, 1=CHAIN, 2=CC, 3=ID)
                washed_relay_ids.add(parts[3])

    # Prepare selector lists
    standard_proxies = []
    standard_tags = []
    for i, p in enumerate(proxies, 1):
        if not p.is_working:
            continue

        # Dirty Pollution Fix: If this proxy was washed, skip adding it to standard list
        # Check if p.id[:6] is in washed_relay_ids
        if p.id[:6] in washed_relay_ids:
            continue

        out = to_singbox_outbound(p)
        if out:
            tag = f"{p.country_code or 'XX'} {i:02d} | {p.protocol.upper()}"
            out["tag"] = tag
            standard_proxies.append(out)
            standard_tags.append(tag)
    washed_tags = [o["tag"] for o in washed_exits]

    # Smart Chain Exits
    intranet_exits = [o for o in smart_chains["intranet"] if "EXIT" in o.get("tag", "")]
    intranet_tags = [o["tag"] for o in intranet_exits]

    ipv6_exits = [o for o in smart_chains["ipv6"] if "EXIT" in o.get("tag", "")]
    ipv6_tags = [o["tag"] for o in ipv6_exits]

    streamer_exits = [o for o in smart_chains["streamer"] if "EXIT" in o.get("tag", "")]
    streamer_tags = [o["tag"] for o in streamer_exits]

    # Collect all outbounds for the config
    all_outbounds = standard_proxies + washed_outbounds
    for chain_list in smart_chains.values():
        all_outbounds.extend(chain_list)

    # 1. singbox-vpn.json (The "Tank")
    vpn_config = {
        "log": {"level": "info"},
        "dns": {
            "servers": [
                {"tag": "google", "address": "8.8.8.8", "detour": "🌍 Proxy Select"},
                {"tag": "local", "address": "223.5.5.5", "detour": "direct"}
            ],
            "rules": [{"outbound": "any", "server": "google"}],
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
                "outbounds": ["🚀 Auto", "🛡️ Washed", "🇮🇷 Intranet"] + standard_tags
            },
            {
                "type": "urltest",
                "tag": "🚀 Auto",
                "outbounds": standard_tags,
                "url": "http://www.gstatic.com/generate_204",
                "interval": "5m"
            },
            {
                "type": "selector",
                "tag": "🛡️ Washed",
                "outbounds": washed_tags if washed_tags else ["direct"]
            },
            {
                "type": "urltest",
                "tag": "🇮🇷 Intranet",
                "outbounds": intranet_tags if intranet_tags else ["direct"],
                "url": "http://www.gstatic.com/generate_204",
                "interval": "5m"
            },
            {"type": "direct", "tag": "direct"},
            {"type": "dns", "tag": "dns-out"}
        ] + all_outbounds
    }

    vpn_file = output_dir / "singbox-vpn.json"
    with open(vpn_file, "w", encoding="utf-8") as f:
        json.dump(vpn_config, f, indent=2)
    files["singbox_vpn"] = vpn_file

    # 2. singbox.json (The "Sniper")
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
                "tag": "🚀 Mode Selector",
                "outbounds": ["⚡ Auto Fast", "🛡️ Secure Washed", "🇮🇷 Intranet Bridge", "🇺🇸 US Streaming", "🌌 IPv6 Portal"]
            },
            {
                "type": "urltest",
                "tag": "⚡ Auto Fast",
                "outbounds": standard_tags,
                "url": "http://www.gstatic.com/generate_204",
                "interval": "5m"
            },
            {
                "type": "urltest",
                "tag": "🛡️ Secure Washed",
                "outbounds": washed_tags if washed_tags else ["direct"],
                "url": "http://www.gstatic.com/generate_204"
            },
            {
                "type": "urltest",
                "tag": "🇮🇷 Intranet Bridge",
                "outbounds": intranet_tags if intranet_tags else ["direct"],
                "url": "http://www.gstatic.com/generate_204"
            },
            {
                "type": "urltest",
                "tag": "🇺🇸 US Streaming",
                "outbounds": streamer_tags if streamer_tags else ["direct"],
                "url": "http://www.gstatic.com/generate_204"
            },
            {
                "type": "urltest",
                "tag": "🌌 IPv6 Portal",
                "outbounds": ipv6_tags if ipv6_tags else ["direct"],
                "url": "http://www.gstatic.com/generate_204"
            },
            {"type": "direct", "tag": "direct"},
            {"type": "dns", "tag": "dns-out"}
        ] + all_outbounds
    }

    # Inject fragmentation for Sniper
    for out in all_outbounds:
        # Be careful only to inject into TLS outbounds that are direct (not chains/selectors)
        # Actually we inject into the OUTBOUND definitions in the list
        if "tls" in out and isinstance(out["tls"], dict):
            out["tls"]["tls_fragment"] = {
                "enabled": True,
                "size": "100-200",
                "sleep": "10-20"
            }

    sniper_file = output_dir / "singbox.json"
    with open(sniper_file, "w", encoding="utf-8") as f:
        json.dump(sniper_config, f, indent=2)
    files["singbox"] = sniper_file

    # 3. clash.yaml (The "Diplomat")
    clash_content = generate_clash_config(proxies)
    clash_file = output_dir / "clash.yaml"
    with open(clash_file, "w", encoding="utf-8") as f:
        f.write(clash_content)
    files["clash"] = clash_file

    return files


def generate_categorized_outputs(
    proxies: List[Proxy],
    output_dir: Path,
    washed_proxies: List[Dict[str, Any]] = None,
) -> Dict[str, Path]:
    """
    Generate files organized by protocol and country.
    """
    if washed_proxies is None:
        washed_proxies = []

    files: Dict[str, Path] = {}

    # 1. Master List (Standard)
    master_file = output_dir / "proxies.json"
    save_json(proxies, master_file, compress=True)
    files["master"] = master_file

    smart_chains = generate_smart_chains(proxies)

    # Save Chains separately (Sing-box only)
    chains_file = output_dir / "singbox-chains.json"
    all_chains = []
    for k, v in smart_chains.items():
        all_chains.extend(v)

    with open(chains_file, "w", encoding="utf-8") as f:
        chain_config = {"outbounds": all_chains}
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
    split_files = generate_split_outputs(proxies, output_dir, washed_proxies, smart_chains)
    files.update(split_files)

    return files


def save_json(proxies: List[Proxy], path: Path, compress: bool = False) -> None:
    """
    Save list of proxies to JSON file atomically with fsync for durability.
    """
    data = [serialize_proxy(p) for p in proxies]
    json_content = json.dumps(data, indent=2, ensure_ascii=False)

    temp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        temp_fd = os.open(str(temp_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        try:
            os.write(temp_fd, json_content.encode("utf-8"))
            os.fsync(temp_fd)
        finally:
            os.close(temp_fd)
        temp_path.replace(path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise

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
    protocols: Dict[str, int] = {}
    countries: Dict[str, int] = {}
    country_stats: Dict[str, int] = {}
    latency_distribution = {"fast": 0, "medium": 0, "slow": 0, "very_slow": 0}

    for p in proxies:
        proto = p.protocol.lower()
        protocols[proto] = protocols.get(proto, 0) + 1
        cc = (p.country_code or "UNK").upper()
        countries[cc] = countries.get(cc, 0) + 1
        country_stats[cc] = country_stats.get(cc, 0) + 1

        latency = p.latency
        if latency is not None and latency > 0:
            if latency < 100: latency_distribution["fast"] += 1
            elif latency < 500: latency_distribution["medium"] += 1
            elif latency < 1000: latency_distribution["slow"] += 1
            else: latency_distribution["very_slow"] += 1
        else:
            latency_distribution["very_slow"] += 1

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
        "latency_distribution": latency_distribution,
        "protocol_colors": {
            "vmess": "#FF6B6B", "vless": "#4ECDC4", "shadowsocks": "#45B7D1",
            "trojan": "#96CEB4", "hysteria": "#FFEAA7", "hysteria2": "#DFE6E9",
            "tuic": "#A29BFE", "wireguard": "#74B9FF", "naive": "#FD79A8",
            "http": "#FDCB6E", "https": "#6C5CE7", "socks": "#00B894",
            "socks5": "#00B894", "openvpn": "#E84393",
        },
    }

    metadata_content = json.dumps(metadata, indent=2)
    for filename in ["metadata.json", "summary.json"]:
        target_path = output_dir / filename
        temp_path = target_path.with_suffix(target_path.suffix + ".tmp")
        try:
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
        if not p.is_working: continue
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

    result = yaml_lib.dump(payload, allow_unicode=True, sort_keys=False)
    return str(result) if result else ""


def generate_singbox_config(proxies: List[Proxy]) -> str:
    """Legacy method for backward compatibility."""
    # Just returns standard config without chains if called directly
    outbounds: List[Dict[str, Any]] = []
    selector_tags: List[str] = []

    for i, p in enumerate(proxies, 1):
        config = to_singbox_outbound(p)
        if config:
            tag = f"{p.country_code or 'XX'} {i:02d} | {p.protocol.upper()}"
            config["tag"] = tag
            outbounds.append(config)
            selector_tags.append(tag)

    if selector_tags:
        outbounds.insert(0, {
            "type": "selector",
            "tag": "🌍 Proxy Select",
            "outbounds": ["🚀 Auto"] + selector_tags,
        })
        outbounds.insert(1, {
            "type": "urltest",
            "tag": "🚀 Auto",
            "outbounds": selector_tags,
            "url": "http://www.gstatic.com/generate_204",
            "interval": "5m",
        })

    full_config = {
        "log": {"level": "info"},
        "inbounds": [{"type": "mixed", "tag": "mixed-in", "listen": "127.0.0.1", "listen_port": 2080}],
        "outbounds": outbounds,
    }

    return json.dumps(full_config, indent=2)


def generate_base64_subscription(proxies: List[Proxy]) -> str:
    """Generate standard Base64 subscription string."""
    lines = []
    for p in proxies:
        if p.config and p.protocol != "openvpn" and "://" in p.config:
            lines.append(p.config)
    text = "\n".join(lines)
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")
