"""
Output Generation Module.
Produces client-compatible configuration files and statistical reports.
"""

import json
import base64
import gzip
import logging
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


def to_clash_proxy(proxy: Proxy) -> Optional[Dict[str, Any]]:
    """Convert internal Proxy model to Clash dictionary."""

    def _add_transport_opts(base: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to add ws/grpc/http options to Clash config."""
        net = details.get("net") or details.get("type") or "tcp"
        base["network"] = net

        if net == "ws":
            ws_opts: Dict[str, Any] = {}
            if "path" in details:
                ws_opts["path"] = str(details["path"])
            if "host" in details or "sni" in details:
                ws_opts["headers"] = {"Host": str(details.get("host") or details.get("sni"))}
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
                base["client-fingerprint"] = str(details.get("fp", "chrome"))  # Reality needs explicit FP often
                base["reality-opts"] = {
                    "public-key": str(details.get("pbk")),
                    "short-id": str(details.get("sid", ""))
                }

        return base

    base: Dict[str, Any] = {}

    if proxy.protocol == "vmess":
        base = {
            "type": "vmess",
            "server": proxy.address,
            "port": proxy.port,
            "uuid": proxy.uuid,
            "alterId": int(proxy.details.get("aid", 0)),
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
            "password": str(proxy.details.get("password", "")) if proxy.details.get("password") else None,
            "tls": proxy.details.get("tls") == "tls",
        }
    elif proxy.protocol == "socks5":
        return {
            "type": "socks5",
            "server": proxy.address,
            "port": proxy.port,
            "username": proxy.uuid if proxy.uuid else None,
            "password": str(proxy.details.get("password", "")) if proxy.details.get("password") else None,
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

    def _add_transport_sb(out: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to add transport options for Sing-box."""
        net = details.get("net") or details.get("type") or "tcp"

        transport: Dict[str, Any] = {}
        if net == "ws":
            transport["type"] = "ws"
            if "path" in details:
                transport["path"] = str(details["path"])
            if "host" in details or "sni" in details:
                transport["headers"] = {"Host": str(details.get("host") or details.get("sni"))}
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
                    "short_id": str(details.get("sid", ""))
                }

            out["tls"] = tls

        return out

    if proxy.protocol == "vmess":
        out = {
            "type": "vmess",
            **base,
            "uuid": proxy.uuid,
            "security": "auto",
            "alter_id": int(proxy.details.get("aid", 0)),
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

    return None


def generate_categorized_outputs(
    proxies: List[Proxy], output_dir: Path
) -> Dict[str, Path]:
    """
    Generate files organized by protocol and country.
    """
    files: Dict[str, Path] = {}

    # 1. Master List
    master_file = output_dir / "proxies.json"
    save_json(
        proxies, master_file, compress=True
    )  # Compress by default for large files
    files["master"] = master_file

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
            os.write(temp_fd, json_content.encode('utf-8'))
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
            temp_fd = os.open(str(temp_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
            try:
                os.write(temp_fd, metadata_content.encode('utf-8'))
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
