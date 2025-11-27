"""
Output Transport Module.
Handles serialization and file I/O for proxy data.
"""

import json
import gzip
import logging
import os
import re
import importlib.metadata
from pathlib import Path
from typing import List, Dict, Union
from datetime import datetime, timezone

from .models import Proxy
from .serialize import serialize_proxy
from .proxy_history import ProxyHistoryTracker
from .utils import AtomicFileWriter

logger = logging.getLogger(__name__)


def save_json(proxies: List[Proxy], path: Path, compress: bool = False) -> None:
    """
    Save list of proxies to JSON file atomically with fsync for durability.
    """
    history = ProxyHistoryTracker()  # Singleton access
    data = [serialize_proxy(p, history.get_history(p.id)) for p in proxies]
    json_content = json.dumps(data, indent=2, ensure_ascii=False)

    try:
        AtomicFileWriter.write_text(path, json_content)
    except Exception:
        raise

    if compress:
        gz_path = Path(str(path) + ".gz")
        try:
            temp_gz_path = gz_path.with_suffix(gz_path.suffix + ".tmp")
            try:
                with gzip.open(temp_gz_path, "wt", encoding="utf-8") as f:
                    f.write(json_content)
                os.replace(temp_gz_path, gz_path)
            except Exception:
                if temp_gz_path.exists():
                    temp_gz_path.unlink()
                raise
        except Exception:
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

    # Enhanced Metadata Tracking
    isp_stats: Dict[str, int] = {}
    city_stats: Dict[str, int] = {}

    for p in proxies:
        proto = p.protocol.lower()
        protocols[proto] = protocols.get(proto, 0) + 1

        cc = (p.country_code or "UNK").upper()
        countries[cc] = countries.get(cc, 0) + 1
        country_stats[cc] = country_stats.get(cc, 0) + 1

        # Track ISP and City if available
        if p.org:
            isp = p.org
            isp_stats[isp] = isp_stats.get(isp, 0) + 1

        if p.city:
            city = f"{p.city}, {cc}"
            city_stats[city] = city_stats.get(city, 0) + 1

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

    total_working = int(stats.get("working", 0))
    fetched_lines = int(stats.get("fetched_lines", 0))
    duration = float(stats.get("duration", 0.0))

    try:
        version = importlib.metadata.version("configstream")
    except Exception:
        version = "unknown"

    metadata = {
        "version": version,
        "last_updated_utc": datetime.now(timezone.utc).isoformat(),
        "total_proxies": len(proxies),
        "total_working": total_working,
        "total_fetched": fetched_lines,
        "duration_seconds": duration,
        "protocols": protocols,
        "countries": countries,
        "country_stats": country_stats,
        "isp_stats": dict(
            sorted(isp_stats.items(), key=lambda x: x[1], reverse=True)[:20]
        ),  # Top 20 ISPs
        "city_stats": dict(
            sorted(city_stats.items(), key=lambda x: x[1], reverse=True)[:20]
        ),  # Top 20 Cities
        "latency_distribution": latency_distribution,
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

    metadata_content = json.dumps(metadata, indent=2)
    for filename in ["metadata.json", "summary.json"]:
        target_path = output_dir / filename
        try:
            AtomicFileWriter.write_text(target_path, metadata_content)
        except Exception:
            raise


def inject_stego_key_into_frontend(secret_key: str, js_file_path: Path) -> None:
    """
    Self-Healing Mechanism:
    Opens the frontend JavaScript file and implants the dynamic secret key
    so the browser can decrypt the latest steganography image.
    """
    if not js_file_path.exists():
        logger.warning(
            f"Frontend JS not found at {js_file_path}, skipping key injection."
        )
        return

    try:
        content = js_file_path.read_text(encoding="utf-8")

        # Regex to find: const SECRET_KEY = "ANYTHING_HERE";
        pattern = r'(const\s+SECRET_KEY\s*=\s*")([^"]*)(")'

        # Use a replacement function to avoid regex interpretation of special chars
        # in the secret_key (e.g., base64 Fernet keys can contain sequences like
        # backslash+digits that would be interpreted as backreferences like \17)
        def replacer(match):
            return match.group(1) + secret_key + match.group(3)

        new_content = re.sub(pattern, replacer, content)

        # Atomic write to prevent corruption
        AtomicFileWriter.write_text(js_file_path, new_content)
        logger.info(f"✅ Successfully injected new Stego Key into {js_file_path.name}")

    except Exception as e:
        logger.error(f"Failed to inject Stego Key: {e}")
