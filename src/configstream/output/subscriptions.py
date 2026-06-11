# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import base64
import os
import tempfile
import zipfile
from typing import List, Dict, Optional, Any
from pathlib import Path

from ..models import Proxy
from ..utils import AtomicFileWriter
from ..constants import (
    protocol_sort_key,
    canonical_protocol_name,
)

logger = logging.getLogger(__name__)

from configstream.generators.plaintext import generate_plaintext_subscription

def generate_base64_subscription(proxies: List[Proxy]) -> str:
    """Generates a Base64-encoded subscription string."""
    content = generate_plaintext_subscription(proxies)
    return base64.b64encode(content.encode("utf-8")).decode("utf-8")

def get_export_pool(proxies: List[Proxy]) -> List[Proxy]:
    """
    Selects the pool of proxies to export in subscription files.
    """
    working = [p for p in proxies if p.is_working]
    if working:
        from configstream.adapters.shadowrocket import ShadowrocketAdapter
        from configstream.generators.plaintext import _extract_uri
        adapter = ShadowrocketAdapter()
        has_valid_uri = False
        for p in working:
            try:
                uri = _extract_uri(p, adapter)
                if uri and uri.strip():
                    has_valid_uri = True
                    break
            except Exception:
                pass
        if has_valid_uri:
            return working
        else:
            return proxies

    non_revived = [
        p
        for p in proxies
        if not (p.protocol == "revived" or (p.details or {}).get("is_revived"))
    ]
    return non_revived if non_revived else proxies

def order_export_proxies(proxies: List[Proxy]) -> List[Proxy]:
    """Deterministic user-facing ordering for URI/adapters/export artifacts."""
    return sorted(
        proxies,
        key=lambda p: (
            protocol_sort_key(p.protocol or "unknown"),
            p.latency is None,
            p.latency if p.latency is not None else 9e9,
            (p.country_code or "ZZ").upper(),
            p.id or "",
        ),
    )

def select_chosen_proxies(
    proxies: List[Proxy],
    top_per_protocol: int,
    total_target: int,
) -> List[Proxy]:
    if top_per_protocol <= 0 and total_target <= 0:
        return []

    pool = get_export_pool(proxies)

    by_protocol: Dict[str, List[Proxy]] = {}
    for proxy in pool:
        proto = canonical_protocol_name(proxy.protocol or "unknown")
        by_protocol.setdefault(proto, []).append(proxy)

    chosen: List[Proxy] = []
    for proto in sorted(by_protocol.keys(), key=protocol_sort_key):
        candidates = sorted(
            by_protocol[proto],
            key=lambda p: (p.latency is None, p.latency or 9e9),
        )
        if top_per_protocol > 0:
            candidates = candidates[:top_per_protocol]
        chosen.extend(candidates)

    if total_target > 0 and len(chosen) > total_target:
        chosen = sorted(chosen, key=lambda p: (p.latency is None, p.latency or 9e9))[
            :total_target
        ]

    return order_export_proxies(chosen)

def generate_side_products_pack(
    proxies: List[Proxy],
    output_path: Path,
    raw_content: str,
    output_dir: Path,
) -> Optional[Path]:
    from .native_configs import build_wireguard_config, _rewrite_openvpn_remote
    
    openvpn_candidates = [
        p
        for p in proxies
        if canonical_protocol_name(p.protocol or "") == "openvpn" and p.config
    ]
    wireguard_candidates = [
        p
        for p in proxies
        if canonical_protocol_name(p.protocol or "") == "wireguard"
    ]
    
    # Simple name sanitization helper
    import re
    safe_re = re.compile(r"[^A-Za-z0-9._-]+")
    def safe_name(val, fallback):
        if not val: return fallback
        clean = safe_re.sub("_", val).strip("._-")
        return clean or fallback

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output_dir, prefix=".side_products.", suffix=".tmp", delete=False
        ) as tmp:
            tmp_path = tmp.name
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("proxies.txt", raw_content)
            for proxy in openvpn_candidates:
                name = safe_name(proxy.remarks or proxy.id, f"openvpn-{proxy.id[:8]}")
                # Check if we need to rewrite for DNS safe/hardened (if address is IP and we have original host)
                details = proxy.details or {}
                if details.get("original_host"):
                    config = _rewrite_openvpn_remote(proxy.config, details["original_host"], proxy.address)
                else:
                    config = proxy.config
                zf.writestr(f"openvpn/{name}.ovpn", config)
            for proxy in wireguard_candidates:
                wg_config = build_wireguard_config(proxy)
                if not wg_config:
                    continue
                name = safe_name(proxy.remarks or proxy.id, f"wireguard-{proxy.id[:8]}")
                zf.writestr(f"wireguard/{name}.conf", wg_config)
        os.replace(tmp_path, output_path)
        return output_path
    except Exception as exc:
        logger.warning("Failed to generate zip: %s", str(exc))
        if tmp_path and os.path.exists(tmp_path):
            try: os.unlink(tmp_path)
            except OSError: pass
    return None

def generate_clash_subscription(proxies: List[Proxy]) -> str:
    from ..generators.clash import generate_clash_config
    return generate_clash_config(proxies)
