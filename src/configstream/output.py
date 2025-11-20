"""
Output Generation Module.
Produces client-compatible configuration files and statistical reports.
"""

import json
import base64
import logging
from pathlib import Path
from typing import List, Dict, Any, Union
from datetime import datetime, timezone

# Fix imports
try:
    import yaml as yaml_lib
except ImportError:
    yaml_lib = None  # type: ignore

from .models import Proxy
from .serialize import serialize_proxy
from .adapters import to_clash_proxy, to_singbox_outbound

logger = logging.getLogger(__name__)


def generate_categorized_outputs(
    proxies: List[Proxy], output_dir: Path
) -> Dict[str, Path]:
    """
    Generate files organized by protocol and country.
    """
    files = {}

    # 1. Master List
    master_file = output_dir / "proxies.json"
    save_json(proxies, master_file)
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


def save_json(proxies: List[Proxy], path: Path) -> None:
    """Save list of proxies to JSON file."""
    data = [serialize_proxy(p) for p in proxies]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def save_metadata(
    stats: Dict[str, Union[int, float]], proxies: List[Proxy], output_dir: Path
) -> None:
    """
    Save metadata.json with statistics for the frontend.
    """
    # Calculate breakdowns
    protocols: Dict[str, int] = {}
    countries: Dict[str, int] = {}

    for p in proxies:
        proto = p.protocol.lower()
        protocols[proto] = protocols.get(proto, 0) + 1

        cc = (p.country_code or "UNK").upper()
        countries[cc] = countries.get(cc, 0) + 1

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
        # Protocol colors for frontend
        "protocol_colors": {
            "vmess": "#FF6B6B",
            "vless": "#4ECDC4",
            "trojan": "#96CEB4",
            "shadowsocks": "#45B7D1",
            "hysteria2": "#DFE6E9",
            "wireguard": "#74B9FF",
        },
    }

    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    # Also save as summary.json for backward compatibility if needed, or just rely on metadata.json
    (output_dir / "summary.json").write_text(json.dumps(metadata, indent=2))


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
    outbounds = []
    selector_tags = []

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
        if p.config and "://" in p.config:
            lines.append(p.config)

    text = "\n".join(lines)
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")
