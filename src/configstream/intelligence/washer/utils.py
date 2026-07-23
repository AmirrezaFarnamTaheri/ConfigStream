# SPDX-License-Identifier: AGPL-3.0-or-later
import base64
import binascii
import hashlib
import ipaddress
from typing import List, Optional

from configstream.config import AppSettings
from configstream.models import Proxy
from configstream.tagging import ProxyTagger, format_proxy_name

DEFAULT_WARP_PEER_KEY = "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo="


def _valid_wireguard_key(value: str) -> bool:
    try:
        decoded = base64.b64decode(str(value), validate=True)
    except (binascii.Error, ValueError, TypeError):
        return False
    return len(decoded) == 32


def make_entry(
    source_tag: str,
    private_key: str,
    address: str,
    peer_pub: Optional[str],
    reserved: List[int],
    port: int = 2408,
) -> Optional[Proxy]:
    """Build an unverified WARP candidate from validated key material."""
    if not _valid_wireguard_key(private_key):
        return None
    peer_key = (
        peer_pub
        if peer_pub and _valid_wireguard_key(peer_pub)
        else DEFAULT_WARP_PEER_KEY
    )

    try:
        normalized_port = int(port)
    except (TypeError, ValueError):
        return None
    if not 1 <= normalized_port <= 65535:
        return None

    normalized_address = str(address or "auto").strip()
    if normalized_address != "auto":
        try:
            normalized_address = str(ipaddress.ip_address(normalized_address))
        except ValueError:
            if not normalized_address or len(normalized_address) > 253:
                return None

    reserved_bytes: list[int] = []
    for value in list(reserved or [])[:3]:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return None
        if not 0 <= number <= 255:
            return None
        reserved_bytes.append(number)
    while len(reserved_bytes) < 3:
        reserved_bytes.append(0)

    proxy_id = hashlib.sha256(private_key.encode("ascii")).hexdigest()[:16]
    digest = hashlib.sha256(private_key.encode("ascii")).digest()
    octet3 = digest[0]
    octet4 = max(digest[1], 2)
    unique_local_ip = f"172.16.{octet3}.{octet4}/32"

    proxy = Proxy(
        config="warp://auto",
        protocol="wireguard",
        address=normalized_address,
        port=normalized_port,
        uuid="",
        remarks="",
        country_code="XX",
        process="warp",
        details={
            "candidate_id": f"WARP-{source_tag}-{proxy_id}",
            "private_key": private_key,
            "peer_public_key": peer_key,
            "reserved": reserved_bytes,
            "mtu": 1280,
            "local_address": unique_local_ip,
        },
        is_working=False,
    )
    template = AppSettings().RENAME_TEMPLATE or ProxyTagger.DEFAULT_TEMPLATE
    proxy.remarks = format_proxy_name(template, proxy) or f"WARP ({source_tag})"
    return proxy
