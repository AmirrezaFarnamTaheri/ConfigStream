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
from .constants import PROTOCOL_COLORS

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
    security_distribution = {"reality": 0, "tls": 0, "none": 0, "other": 0}
    transport_distribution: Dict[str, int] = {}
    working_by_protocol: Dict[str, int] = {}
    total_latency = 0.0
    latency_count = 0

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

        # Track security type
        if p.details:
            sec = p.details.get("security", "none")
            if sec == "reality":
                security_distribution["reality"] += 1
            elif sec in ("tls", "xtls"):
                security_distribution["tls"] += 1
            elif sec in ("none", ""):
                security_distribution["none"] += 1
            else:
                security_distribution["other"] += 1

            # Track transport type
            transport = p.details.get("type") or p.details.get("net") or "tcp"
            transport_distribution[transport] = (
                transport_distribution.get(transport, 0) + 1
            )

        # Track working by protocol
        if p.is_working:
            working_by_protocol[proto] = working_by_protocol.get(proto, 0) + 1

        latency = p.latency
        if latency and latency > 0:
            total_latency += latency
            latency_count += 1
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
    parsed_count = int(stats.get("parsed", 0))
    duration = float(stats.get("duration", 0.0))

    try:
        version = importlib.metadata.version("configstream")
    except Exception:
        version = "unknown"

    # Normalize inputs to avoid negative or >parsed anomalies
    safe_working = max(0, int(total_working))
    safe_parsed = max(0, int(parsed_count))
    safe_fetched = max(0, int(fetched_lines))

    if safe_parsed > 0:
        success_rate = (safe_working / safe_parsed) * 100.0
    elif safe_fetched > 0:
        success_rate = (safe_working / safe_fetched) * 100.0
    else:
        success_rate = 0.0

    success_rate = round(min(100.0, max(0.0, success_rate)), 2)

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
        "security_distribution": security_distribution,
        "transport_distribution": dict(
            sorted(transport_distribution.items(), key=lambda x: x[1], reverse=True)
        ),
        "working_by_protocol": working_by_protocol,
        "quality_metrics": {
            "success_rate": success_rate,
            "avg_latency": (
                round(total_latency / latency_count, 2) if latency_count > 0 else 0
            ),
        },
        "protocol_colors": PROTOCOL_COLORS,
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
