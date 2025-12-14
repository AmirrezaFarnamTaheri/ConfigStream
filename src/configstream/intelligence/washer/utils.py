from typing import Optional, List
from ...models import Proxy


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
    import hashlib

    proxy_id = hashlib.sha256(private_key.encode()).hexdigest()[:16]

    details = {
        "private_key": private_key,
        "peer_public_key": peer_pub
        or "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",  # Default Cloudflare Pub
        "reserved": reserved,
        "mtu": 1280,
        "local_address": "172.16.0.2/32",  # Default, washer will rotate this
    }

    return Proxy(
        config="warp://auto",
        protocol="wireguard",
        address=address,
        port=port,
        uuid=f"WARP-{source_tag}-{proxy_id}",
        remarks=f"WARP ({source_tag})",
        country_code="XX",  # Unknown until tested
        details=details,
        is_working=True,  # Assume working until tested
    )
