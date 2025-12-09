"""
WARP Configuration Scraper
First fallback source for WARP endpoints and keys.

LEGAL & COMPLIANCE NOTICE:
This module scrapes public repositories for WARP configurations.
- Keys are sourced from public commits on GitHub.
- ConfigStream does not generate or crack keys.
- Use at your own risk. This feature is intended for censorship circumvention in restricted regions.
- To opt-out your repository, please contact the maintainers or make your repo private.
"""

import json
import logging
import base64
import binascii
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

PEER_PUBLIC_KEY_DEFAULT = "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo="

WARP_SOURCES: List[Dict[str, Any]] = [
    {
        "name": "amin4139/Wireguard.txt",
        "url": "https://raw.githubusercontent.com/amin4139/share_file/main/Wireguard.txt",
        "kind": "singbox",
        "max_entries": 32,
    },
    {
        "name": "amin4139/Hiddify+",
        "url": "https://raw.githubusercontent.com/amin4139/share_file/main/Hiddify%2B",
        "kind": "singbox",
        "max_entries": 32,
    },
    {
        "name": "amin4139/Wireguard_hiddify",
        "url": "https://raw.githubusercontent.com/amin4139/share_file/main/Wireguard_hiddify",
        "kind": "singbox",
        "max_entries": 32,
    },
    {
        "name": "amin4139/Wireguard_xray.txt",
        "url": "https://raw.githubusercontent.com/amin4139/share_file/main/Wireguard_xray.txt",
        "kind": "xray_wireguard",
        "max_entries": 32,
    },
    {
        "name": "ByteMysticRogue/Hiddify-Warp/sing-box.json",
        "url": "https://raw.githubusercontent.com/ByteMysticRogue/Hiddify-Warp/main/sing-box.json",
        "kind": "singbox",
        "max_entries": 64,
    },
    {
        "name": "NiREvil/vless/sing-box.json",
        "url": "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sing-box.json",
        "kind": "singbox_endpoints",
        "max_entries": 64,
    },
    {
        "name": "arshiacomplus/WoW-fix/sing-box-hiddify.json",
        "url": "https://raw.githubusercontent.com/arshiacomplus/WoW-fix/main/sing-box-hiddify.json",
        "kind": "singbox",
        "max_entries": 32,
    },
]

TIMEOUT_SECONDS = 20


def looks_like_private_key(s: Any) -> bool:
    """Validate WireGuard private key format."""
    if not isinstance(s, str):
        return False
    s = s.strip()
    if not s or " " in s or "\n" in s:
        return False
    if len(s) < 40 or len(s) > 100:
        return False
    try:
        base64.b64decode(s, validate=True)
    except binascii.Error:
        return False
    return True


def pick_local_address(addr_field: Any) -> Optional[str]:
    """Extract IPv4 local address from various formats."""
    if isinstance(addr_field, str):
        return addr_field
    if isinstance(addr_field, list):
        for a in addr_field:
            if isinstance(a, str) and "." in a:
                return a
        for a in addr_field:
            if isinstance(a, str):
                return a
    return None


def normalize_reserved(value: Any) -> List[int]:
    """Normalize reserved field to [int, int, int]."""
    if isinstance(value, list) and len(value) >= 3:
        out = []
        for x in value[:3]:
            try:
                n = max(0, min(255, int(x)))
            except (TypeError, ValueError):
                n = 0
            out.append(n)
        return out
    return [0, 0, 0]


def make_entry(
    tag: str,
    private_key: Any,
    local_address_field: Any,
    peer_public_key: Optional[str],
    reserved_field: Any,
) -> Optional[Dict[str, Any]]:
    """Create a standardized WARP entry."""
    if not looks_like_private_key(private_key):
        return None

    local_address = pick_local_address(local_address_field)
    if not local_address:
        return None

    reserved = normalize_reserved(reserved_field)
    peer_key = peer_public_key or PEER_PUBLIC_KEY_DEFAULT

    return {
        "id": str(tag),
        "private_key": str(private_key).strip(),
        "peer_public_key": str(peer_key),
        "local_address": str(local_address),
        "reserved": reserved,
    }


def extract_from_outbounds(
    config: Dict[str, Any], max_entries: int
) -> List[Dict[str, Any]]:
    """Extract WireGuard entries from Sing-box style outbounds."""
    results: List[Dict[str, Any]] = []

    def walk(obj: Any) -> None:
        if len(results) >= max_entries:
            return

        if isinstance(obj, dict):
            if obj.get("type") == "wireguard" and (
                "local_address" in obj or "address" in obj
            ):
                entry = make_entry(
                    obj.get("tag", "wg"),
                    obj.get("private_key"),
                    obj.get("local_address", obj.get("address")),
                    obj.get("peer_public_key"),
                    obj.get("reserved", [0, 0, 0]),
                )
                if entry:
                    results.append(entry)

            for v in obj.values():
                walk(v)

        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(config)
    return results


def extract_from_xray_wireguard(
    config: Dict[str, Any], max_entries: int
) -> List[Dict[str, Any]]:
    """Extract WireGuard entries from Xray format."""
    results: List[Dict[str, Any]] = []
    outbounds = config.get("outbounds", [])

    for ob in outbounds:
        if len(results) >= max_entries:
            break
        if ob.get("protocol") != "wireguard":
            continue

        settings = ob.get("settings", {})
        peers = settings.get("peers", [])
        peer_key = None
        reserved = [0, 0, 0]

        if peers and isinstance(peers[0], dict):
            peer_key = peers[0].get("publicKey")
            reserved = peers[0].get("reserved", [0, 0, 0])

        entry = make_entry(
            ob.get("tag", "wg-xray"),
            settings.get("secretKey") or settings.get("private_key"),
            settings.get("address"),
            peer_key,
            reserved,
        )
        if entry:
            results.append(entry)

    return results


async def scrape_warp_sources() -> List[Dict[str, Any]]:
    """Scrape all WARP sources and return deduplicated entries."""
    all_entries = []

    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        for src in WARP_SOURCES:
            try:
                logger.debug(f"Fetching WARP source: {src['name']}")
                resp = await client.get(src["url"])

                if resp.status_code != 200:
                    continue

                text = resp.text.strip()
                if not text:
                    continue

                # Try to parse JSON
                try:
                    config = json.loads(text)
                except json.JSONDecodeError:
                    # Try extracting JSON from garbage
                    start = text.find("{")
                    end = text.rfind("}")
                    if start != -1 and end > start:
                        try:
                            config = json.loads(text[start : end + 1])
                        except Exception:
                            continue
                    else:
                        continue

                if not isinstance(config, dict):
                    continue

                # Extract based on kind
                kind = src["kind"]
                max_entries = src.get("max_entries", 32)

                if kind == "singbox":
                    entries = extract_from_outbounds(config, max_entries)
                elif kind == "singbox_endpoints":
                    entries = extract_from_outbounds(config, max_entries)
                elif kind == "xray_wireguard":
                    entries = extract_from_xray_wireguard(config, max_entries)
                else:
                    entries = []

                logger.info(f"WARP source {src['name']}: found {len(entries)} entries")
                all_entries.extend(entries)

            except Exception as e:
                logger.debug(f"WARP source {src['name']} failed: {e}")
                continue

    # Deduplicate
    seen = set()
    unique: List[Dict[str, Any]] = []
    for item in all_entries:
        key = (item["private_key"], item["local_address"])
        if key not in seen:
            seen.add(key)
            unique.append(item)

    logger.info(
        f"WARP scraper: {len(unique)} unique entries from {len(all_entries)} total"
    )
    return unique
