"""
Output Generation Module.
Produces client-compatible configuration files and statistical reports.
"""

import base64
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml
except ImportError:
    yaml = None

from .models import Proxy
from .selection import select_chosen_proxies
from .serialize import dumps, dump_to_path
from .adapters import to_clash_proxy, to_singbox_outbound

def get_country_flag(country_code: str) -> str:
    """Convert country code to flag emoji."""
    if not country_code or len(country_code) != 2:
        return "🏁"
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in country_code.upper())

def _generate_formatted_name(proxy: Proxy, rank: int) -> str:
    """Generate a standardized display name for clients."""
    flag = get_country_flag(proxy.country_code)
    clean_proto = proxy.protocol.upper()
    # Format: "🇺🇸 US 01 | VMESS | 120ms"
    latency = f"{int(proxy.latency)}ms" if proxy.latency else "TIMEOUT"
    return f"{flag} {proxy.country_code} {rank:02d} | {clean_proto} | {latency}"

def generate_categorized_outputs(all_proxies: List[Proxy], output_dir: Path) -> Dict[str, str]:
    """
    Generate categorized output files using optimized serialization.
    """
    output_files = {}

    # Sort globally by latency for consistent ranking
    all_proxies.sort(key=lambda p: p.latency if p.latency else 999999)

    passed = [p for p in all_proxies if p.is_working]
    failed = [p for p in all_proxies if not p.is_working]

    # --- Helper: Serialization with Adapter Injection ---
    def _serialize_list(proxies: List[Proxy]) -> List[Dict]:
        # We convert to a raw dict for JSON output, not client config
    return [p.model_dump() for p in proxies]

    # 1. Protocol Categorization
    protocol_dir = output_dir / "by_protocol"
    protocol_dir.mkdir(parents=True, exist_ok=True)

    by_proto: Dict[str, List[Proxy]] = {}
    for p in passed:
        by_proto.setdefault(p.protocol, []).append(p)

    for proto, plist in by_proto.items():
        fpath = protocol_dir / f"{proto}.json"
        dump_to_path(fpath, _serialize_list(plist))
        output_files[f"protocol_{proto}"] = str(fpath)

    # 2. Country Categorization
    country_dir = output_dir / "by_country"
    country_dir.mkdir(parents=True, exist_ok=True)

    by_country: Dict[str, List[Proxy]] = {}
    for p in passed:
        code = p.country_code.lower() if p.country_code else "unknown"
        by_country.setdefault(code, []).append(p)

    for code, plist in by_country.items():
        fpath = country_dir / f"{code}.json"
        dump_to_path(fpath, _serialize_list(plist))
        output_files[f"country_{code}"] = str(fpath)

    # 3. Rejected / Debug
    rejected_dir = output_dir / "rejected"
    rejected_dir.mkdir(parents=True, exist_ok=True)

    dump_to_path(rejected_dir / "failed.json", _serialize_list(failed))
    output_files["rejected_failed"] = str(rejected_dir / "failed.json")

    # 4. Summary
    summary = {
        "total": len(all_proxies),
        "working": len(passed),
        "protocols": {k: len(v) for k, v in by_proto.items()},
        "countries": {k: len(v) for k, v in by_country.items()}
    }
    dump_to_path(output_dir / "summary.json", summary)
    output_files["summary"] = str(output_dir / "summary.json")

    return output_files

def generate_clash_config(proxies: List[Proxy]) -> str:
    """Generate valid Clash Meta YAML."""
    if yaml is None:
        return "# PyYAML not installed"

    clash_proxies = []
    names = []

    for i, p in enumerate(proxies, 1):
        # Generate name *here* to avoid mutating the proxy object
        display_name = _generate_formatted_name(p, i)

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
                "proxies": names
            },
            {
                "name": "🌍 Proxy Select",
                "type": "select",
                "proxies": names + ["🚀 ConfigStream Auto"]
            }
        ],
        "rules": ["MATCH,🚀 ConfigStream Auto"]
    }

    # Allow unicode output for flags
    return yaml.dump(payload, allow_unicode=True, sort_keys=False)

def generate_singbox_config(proxies: List[Proxy]) -> str:
    """Generate Sing-box JSON config."""
    outbounds = []
    selector_tags = []

    for i, p in enumerate(proxies, 1):
        config = to_singbox_outbound(p)
        if config:
            tag = _generate_formatted_name(p, i)
            config["tag"] = tag
            outbounds.append(config)
            selector_tags.append(tag)

    # Add selector and auto groups
    outbounds.insert(0, {
        "type": "selector",
        "tag": "🌍 Proxy Select",
        "outbounds": ["🚀 Auto"] + selector_tags
    })
    outbounds.insert(1, {
        "type": "urltest",
        "tag": "🚀 Auto",
        "outbounds": selector_tags,
        "url": "http://www.gstatic.com/generate_204",
        "interval": "5m"
    })

    # Basic structure
    full_config = {
        "log": {"level": "info"},
        "inbounds": [
            {"type": "mixed", "tag": "mixed-in", "listen": "127.0.0.1", "listen_port": 2080}
        ],
        "outbounds": outbounds
    }

    return dumps(full_config)

def generate_base64_subscription(proxies: List[Proxy]) -> str:
    """Generate simple Base64 subscription."""
    # Just raw configs joined by newline
    valid_lines = [p.config for p in proxies if p.config]
    raw_str = "\n".join(valid_lines)
    return base64.b64encode(raw_str.encode("utf-8")).decode("utf-8")
