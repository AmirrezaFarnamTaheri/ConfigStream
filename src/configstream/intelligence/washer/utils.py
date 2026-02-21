# SPDX-License-Identifier: AGPL-3.0-or-later
import hashlib
from typing import Optional, List
from configstream.models import Proxy
from configstream.tagging import format_proxy_name, ProxyTagger
from configstream.config import AppSettings


def make_entry(
    source_tag: str,
    private_key: str,
    address: str,
    peer_pub: Optional[str],
    reserved: List[int],
    port: int = 2408,
) -> Optional[Proxy]:
    """
    Helper to create a WARP Proxy object from scraped credentials.
    """
    if not private_key:
        return None

    # Basic validation of keys (length check for base64)
    if len(private_key) < 40:
        return None

    # Construct the proxy
    # We use a deterministic UUID based on the private key hash for stability
    proxy_id = hashlib.sha256(private_key.encode()).hexdigest()[:16]

    # Generate unique local IP based on private key to prevent collisions
    # Hash the private key to generate unique IP address in 172.16.0.0/16 range
    h = hashlib.sha256(private_key.encode()).digest()
    octet3 = h[0]
    octet4 = h[1]
    # Ensure fourth octet is not .0 or .1 which can be special
    octet4 = max(octet4, 2)
    unique_local_ip = f"172.16.{octet3}.{octet4}/32"

    details = {
        "private_key": private_key,
        "peer_public_key": peer_pub
        or "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",  # Default Cloudflare Pub
        "reserved": reserved,
        "mtu": 1280,
        "local_address": unique_local_ip,  # Unique IP based on private key
    }

    proxy = Proxy(
        config="warp://auto",
        protocol="wireguard",
        address=address,
        port=port,
        uuid=f"WARP-{source_tag}-{proxy_id}",
        remarks="",
        country_code="XX",  # Unknown until tested
        process="warp",
        details=details,
        is_working=True,  # Assume working until tested
    )
    # Unified scheme: geo | tech/protocol stack | latency | process | etc
    tpl = AppSettings().RENAME_TEMPLATE or ProxyTagger.DEFAULT_TEMPLATE
    proxy.remarks = format_proxy_name(tpl, proxy) or f"WARP ({source_tag})"
    return proxy
