# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import logging
import copy
import shutil
import os
import re
import tempfile
import zipfile
import ipaddress
import hashlib
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime, timezone
from importlib.metadata import version

from .models import Proxy
from .converters.common import safe_int_conversion
from .generators import (
    generate_singbox_config,
    generate_base64_subscription,
    generate_split_outputs,
)
from .adapters import get_adapter, ShadowrocketAdapter
from .generators.plaintext import generate_plaintext_subscription
from .intelligence.chaining import generate_smart_chains
from .intelligence.washer.core import ProxyWasher
from .utils import AtomicFileWriter
from .config import AppSettings
from .constants import CHOSEN_TOP_PER_PROTOCOL, CHOSEN_TOTAL_TARGET
from .dns_profiles import (
    build_singbox_dns_profile,
    build_clash_dns_profile,
    build_resolver_sets,
)

logger = logging.getLogger(__name__)


def _safe_filename(value: str, fallback: str) -> str:
    if not value:
        return fallback
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return clean or fallback


def _add_suffix(filename: str, suffix: str) -> str:
    if not suffix:
        return filename
    base, ext = os.path.splitext(filename)
    return f"{base}{suffix}{ext}"


def _normalize_host(value: str) -> str:
    return value.strip().lower().rstrip(".")


def _is_ip_literal(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _is_global_ip(value: str) -> bool:
    try:
        return bool(ipaddress.ip_address(value).is_global)
    except ValueError:
        return False


def _rewrite_openvpn_remote(config: str, original_host: str, ip_value: str) -> str:
    if not config or not original_host or not ip_value:
        return config
    out_lines: List[str] = []
    for line in config.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            out_lines.append(line)
            continue
        if stripped.lower().startswith("remote "):
            parts = stripped.split()
            if len(parts) >= 2 and _normalize_host(parts[1]) == _normalize_host(
                original_host
            ):
                parts[1] = ip_value
                line = " ".join(parts)
        out_lines.append(line)
    return "\n".join(out_lines) + ("\n" if config.endswith("\n") else "")


def _build_dns_safe_proxies(
    proxies: List[Proxy],
) -> Tuple[List[Proxy], Dict[str, str]]:
    safe: List[Proxy] = []
    host_map: Dict[str, str] = {}
    adapter = ShadowrocketAdapter()

    for proxy in proxies:
        addr = (proxy.address or "").strip()
        if not addr:
            continue

        # If already IP, keep as-is (only global/public addresses).
        if _is_ip_literal(addr):
            if _is_global_ip(addr):
                safe.append(proxy)
                host_map[_normalize_host(addr)] = addr
            continue

        resolved = (proxy.resolved_ip or "").strip()
        if not resolved or not _is_ip_literal(resolved) or not _is_global_ip(resolved):
            continue

        host_map[_normalize_host(addr)] = resolved

        clone = proxy.model_copy(deep=True)
        clone.address = resolved
        clone.resolved_ip = resolved

        details = dict(clone.details or {})
        details.setdefault("_origin_id", proxy.id)
        details.setdefault("original_host", addr)
        if not details.get("sni"):
            details["sni"] = addr
        if (
            not details.get("host")
            and not details.get("http_host")
            and not details.get("ws_host")
        ):
            details["host"] = addr
        if details.get("server_name") is None:
            details["server_name"] = addr
        clone.details = details

        if isinstance(clone.config, str) and "://" in clone.config:
            rebuilt = adapter._reconstruct_uri(clone)
            clone.config = rebuilt or ""

        safe.append(clone)

    return safe, host_map


def _build_dns_hardened_proxies(
    proxies: List[Proxy],
) -> Tuple[List[Proxy], Dict[str, str]]:
    """
    DNS-hardened proxies prefer IPs when available but do not drop
    entries that could not be resolved.
    """
    hardened: List[Proxy] = []
    host_map: Dict[str, str] = {}
    adapter = ShadowrocketAdapter()

    for proxy in proxies:
        addr = (proxy.address or "").strip()
        if not addr:
            continue

        if _is_ip_literal(addr):
            hardened.append(proxy)
            continue

        resolved = (proxy.resolved_ip or "").strip()
        if resolved and _is_ip_literal(resolved) and _is_global_ip(resolved):
            host_map[_normalize_host(addr)] = resolved

            clone = proxy.model_copy(deep=True)
            clone.address = resolved
            clone.resolved_ip = resolved

            details = dict(clone.details or {})
            details.setdefault("_origin_id", proxy.id)
            details.setdefault("original_host", addr)
            if not details.get("sni"):
                details["sni"] = addr
            if (
                not details.get("host")
                and not details.get("http_host")
                and not details.get("ws_host")
            ):
                details["host"] = addr
            if details.get("server_name") is None:
                details["server_name"] = addr
            clone.details = details

            if isinstance(clone.config, str) and "://" in clone.config:
                rebuilt = adapter._reconstruct_uri(clone)
                clone.config = rebuilt or ""

            hardened.append(clone)
        else:
            hardened.append(proxy)

    return hardened, host_map


def _rewrite_outbound_for_dns_safe(
    outbound: Dict[str, Any], host_map: Dict[str, str]
) -> Optional[Dict[str, Any]]:
    server = outbound.get("server")
    if isinstance(server, str) and server:
        if _is_ip_literal(server):
            if not _is_global_ip(server):
                return None
            return outbound
        mapped = host_map.get(_normalize_host(server))
        if not mapped:
            return None
        outbound["server"] = mapped
        tls = outbound.get("tls")
        if isinstance(tls, dict) and not tls.get("server_name"):
            tls = dict(tls)
            tls["server_name"] = server
            outbound["tls"] = tls
        if not outbound.get("sni"):
            outbound["sni"] = server
    return outbound


def _rewrite_outbound_for_dns_hardened(
    outbound: Dict[str, Any], host_map: Dict[str, str]
) -> Dict[str, Any]:
    server = outbound.get("server")
    if isinstance(server, str) and server:
        if _is_ip_literal(server):
            return outbound
        mapped = host_map.get(_normalize_host(server))
        if mapped:
            outbound["server"] = mapped
            tls = outbound.get("tls")
            if isinstance(tls, dict) and not tls.get("server_name"):
                tls = dict(tls)
                tls["server_name"] = server
                outbound["tls"] = tls
            if not outbound.get("sni"):
                outbound["sni"] = server
    return outbound


def _filter_outbounds_for_dns_safe(
    outbounds: List[Dict[str, Any]], host_map: Dict[str, str]
) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    for outbound in outbounds:
        if not isinstance(outbound, dict):
            continue
        candidate = copy.deepcopy(outbound)
        if "server" in candidate:
            candidate = _rewrite_outbound_for_dns_safe(candidate, host_map)
            if candidate is None:
                continue
        cleaned.append(candidate)

    changed = True
    while changed:
        changed = False
        tags = {o.get("tag") for o in cleaned if o.get("tag")}
        new_cleaned: List[Dict[str, Any]] = []
        for outbound in cleaned:
            detour = outbound.get("detour")
            if detour and detour not in tags:
                changed = True
                continue
            if isinstance(outbound.get("outbounds"), list):
                filtered = [t for t in outbound["outbounds"] if t in tags]
                if not filtered:
                    changed = True
                    continue
                if filtered != outbound["outbounds"]:
                    outbound = dict(outbound)
                    outbound["outbounds"] = filtered
            new_cleaned.append(outbound)
        cleaned = new_cleaned

    return cleaned


def _filter_outbounds_for_dns_hardened(
    outbounds: List[Dict[str, Any]], host_map: Dict[str, str]
) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    for outbound in outbounds:
        if not isinstance(outbound, dict):
            continue
        candidate = copy.deepcopy(outbound)
        if "server" in candidate:
            candidate = _rewrite_outbound_for_dns_hardened(candidate, host_map)
        cleaned.append(candidate)

    changed = True
    while changed:
        changed = False
        tags = {o.get("tag") for o in cleaned if o.get("tag")}
        new_cleaned: List[Dict[str, Any]] = []
        for outbound in cleaned:
            detour = outbound.get("detour")
            if detour and detour not in tags:
                changed = True
                continue
            if isinstance(outbound.get("outbounds"), list):
                filtered = [t for t in outbound["outbounds"] if t in tags]
                if not filtered:
                    changed = True
                    continue
                if filtered != outbound["outbounds"]:
                    outbound = dict(outbound)
                    outbound["outbounds"] = filtered
            new_cleaned.append(outbound)
        cleaned = new_cleaned

    return cleaned


def _dns_resolver_sets() -> Tuple[List[str], List[str]]:
    primary, fallback = build_resolver_sets()
    if not primary:
        logger.warning("DNS-hardened outputs: resolver list is empty.")
    return primary, fallback


def _render_dns_comment_block(primary: List[str], fallback: List[str]) -> List[str]:
    lines = ["# DNS resolvers (DoH/DoT/DoQ):"]
    for resolver in primary:
        lines.append(f"# - {resolver}")
    if fallback:
        lines.append("# DNS fallback order:")
        for resolver in fallback:
            lines.append(f"# - {resolver}")
    return lines


def _wrap_surge_or_loon_profile(
    adapter_name: str,
    proxies: List[Proxy],
    washed_outbounds: Optional[List[Dict[str, Any]]],
    primary: List[str],
    fallback: List[str],
) -> str:
    adapter = get_adapter(adapter_name)
    content = (
        adapter.export(proxies, washed_outbounds=washed_outbounds)
        if adapter_name in ("surge", "loon")
        else adapter.export(proxies)
    )
    proxy_lines = content.splitlines()
    if proxy_lines and proxy_lines[0].startswith("#"):
        proxy_lines = proxy_lines[1:]
    lines = [
        f"# ConfigStream DNS-hardened profile ({adapter_name})",
        "# Prefer IP when available; SNI/Host pinned for TLS.",
        "[Proxy]",
    ]
    lines.extend(proxy_lines)
    lines.extend(["", "[DNS]"])
    if primary:
        lines.append(f"dns-server = {', '.join(primary)}")
    if fallback:
        lines.append(f"fallback-dns-server = {', '.join(fallback)}")
    return "\n".join(lines).rstrip() + "\n"


def _wrap_quantumultx_profile(
    proxies: List[Proxy],
    primary: List[str],
    fallback: List[str],
) -> str:
    adapter = get_adapter("quantumultx")
    content = adapter.export(proxies)
    proxy_lines = content.splitlines()
    lines = [
        "# ConfigStream DNS-hardened profile (quantumultx)",
        "# Prefer IP when available; SNI/Host pinned for TLS.",
        "[server_local]",
    ]
    lines.extend(proxy_lines)
    lines.extend(["", "[dns]"])
    for resolver in primary:
        lines.append(f"server={resolver}")
    for resolver in fallback:
        lines.append(f"server={resolver}")
    return "\n".join(lines).rstrip() + "\n"


def _wrap_shadowrocket_profile(
    proxies: List[Proxy],
    primary: List[str],
    fallback: List[str],
) -> str:
    adapter = get_adapter("shadowrocket")
    content = adapter.export(proxies)
    lines = [
        "# ConfigStream DNS-hardened list (Shadowrocket)",
        "# Prefer IP when available; SNI/Host pinned for TLS.",
    ]
    lines.extend(_render_dns_comment_block(primary, fallback))
    if content:
        lines.append("")
        lines.append("# Proxy list")
        lines.extend(content.splitlines())
    return "\n".join(lines).rstrip() + "\n"


def _build_wireguard_config(proxy: Proxy) -> Optional[str]:
    details = proxy.details or {}
    private_key = details.get("private_key") or proxy.uuid or ""
    peer_public_key = details.get("peer_public_key") or details.get("public_key") or ""

    local_address = details.get("local_address") or details.get("private_ipv4")
    addresses: List[str] = []
    if isinstance(local_address, list):
        addresses = [str(item) for item in local_address if item]
    elif isinstance(local_address, str) and local_address:
        addresses = [local_address]

    if not private_key or not peer_public_key:
        return None

    allowed_ips = details.get("allowed_ips") or "0.0.0.0/0, ::/0"
    endpoint = f"{proxy.address}:{proxy.port}"
    keepalive = details.get("persistent_keepalive") or details.get("keepalive")
    dns = details.get("dns")

    lines = [
        "[Interface]",
        f"PrivateKey = {private_key}",
    ]
    if addresses:
        lines.append(f"Address = {', '.join(addresses)}")
    if dns:
        lines.append(f"DNS = {dns}")
    lines.append("")
    lines.extend(
        [
            "[Peer]",
            f"PublicKey = {peer_public_key}",
            f"AllowedIPs = {allowed_ips}",
            f"Endpoint = {endpoint}",
        ]
    )
    if keepalive:
        lines.append(f"PersistentKeepalive = {keepalive}")

    return "\n".join(lines) + "\n"


def _select_chosen_proxies(proxies: List[Proxy]) -> List[Proxy]:
    if CHOSEN_TOP_PER_PROTOCOL <= 0 and CHOSEN_TOTAL_TARGET <= 0:
        return []

    by_protocol: Dict[str, List[Proxy]] = {}
    for proxy in proxies:
        if not proxy.is_working:
            continue
        proto = (proxy.protocol or "unknown").lower()
        by_protocol.setdefault(proto, []).append(proxy)

    chosen: List[Proxy] = []
    for proto in sorted(by_protocol.keys()):
        candidates = sorted(
            by_protocol[proto],
            key=lambda p: (p.latency is None, p.latency or 9e9),
        )
        if CHOSEN_TOP_PER_PROTOCOL > 0:
            candidates = candidates[:CHOSEN_TOP_PER_PROTOCOL]
        chosen.extend(candidates)

    if CHOSEN_TOTAL_TARGET > 0 and len(chosen) > CHOSEN_TOTAL_TARGET:
        chosen = sorted(chosen, key=lambda p: (p.latency is None, p.latency or 9e9))[
            :CHOSEN_TOTAL_TARGET
        ]

    return chosen


def generate_categorized_outputs(
    proxies: List[Proxy],
    output_dir: Path,
    washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    washed_ids: Optional[set] = None,
    smart_chains: Optional[Dict[str, List[List[Dict[str, Any]]]]] = None,
    washer: Optional[ProxyWasher] = None,  # Pass existing washer instance
) -> Dict[str, Path]:
    """
    Generates all output files categorized by protocol, country, and type.
    Now includes Smart Chains and Washed Proxies.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files = {}

    # Remove legacy redundant artifacts to keep output clean and canonical.
    legacy_files = ["raw.txt", "all.txt", "sub.txt", "vpn_subscription_base64.txt"]
    for name in legacy_files:
        legacy_path = output_dir / name
        if legacy_path.exists():
            try:
                legacy_path.unlink()
            except OSError:
                pass

    for legacy_dir in ("by_country", "by_protocol"):
        legacy_path = output_dir / legacy_dir
        if legacy_path.exists() and legacy_path.is_dir():
            try:
                shutil.rmtree(legacy_path)
            except OSError:
                pass

    # Initialize washer if not provided (fallback)
    if washer is None:
        washer = ProxyWasher(AppSettings().WARP_KEY_POOL)

    # 1. Generate Smart Chains if not provided
    if smart_chains is None:
        if AppSettings().ENABLE_SMART_CHAINING:
            smart_chains = generate_smart_chains(proxies, washer=washer)
        else:
            smart_chains = {}

    # 2. Generate Split Outputs (The Tank & The Sniper & Clash)
    # This restores singbox-vpn.json (Tank) and singbox.json (Sniper)
    split_files = generate_split_outputs(
        proxies,
        output_dir,
        washed_outbounds=washed_outbounds,
        washed_ids=washed_ids,
        smart_chains=smart_chains,
    )
    generated_files.update(split_files)

    # Map for legacy tests/expectations
    if "singbox" in split_files:
        generated_files["singbox_full"] = split_files["singbox"]
        # Legacy test might expect "master" key?
        generated_files["master"] = split_files["singbox"]
    if "singbox_vpn" in split_files:
        generated_files["singbox_vpn"] = split_files["singbox_vpn"]
    if "clash" in split_files:
        generated_files["clash_full"] = split_files["clash"]

    # 3. Standard Subscription (Base64)
    sub_content = generate_base64_subscription(proxies)
    base64_path = output_dir / "base64.txt"
    AtomicFileWriter.write_text(base64_path, sub_content)
    generated_files["base64"] = base64_path

    # 3b. Raw URI list (Plaintext) - single canonical file to avoid redundancy
    raw_content = generate_plaintext_subscription(proxies)
    proxies_txt_path = output_dir / "proxies.txt"
    AtomicFileWriter.write_text(proxies_txt_path, raw_content)
    generated_files["proxies_txt"] = proxies_txt_path

    # 3c. Chosen subset (top per protocol)
    chosen = _select_chosen_proxies(proxies)
    if chosen:
        chosen_dir = output_dir / "chosen"
        chosen_dir.mkdir(exist_ok=True)
        chosen_base64 = generate_base64_subscription(chosen)
        chosen_base64_path = chosen_dir / "base64.txt"
        AtomicFileWriter.write_text(chosen_base64_path, chosen_base64)
        generated_files["chosen_base64"] = chosen_base64_path

    # 3d. Adapter-specific outputs (Shadowrocket, QuantumultX, Surge, Loon, SIP008)
    adapter_specs = {
        "shadowrocket": ("shadowrocket", "shadowrocket.txt"),
        "quantumult": ("quantumultx", "quantumult.conf"),
        "surge": ("surge", "surge.conf"),
        "loon": ("loon", "loon.conf"),
        "sip008": ("sip008", "sip008.json"),
    }
    for key, (adapter_name, filename) in adapter_specs.items():
        try:
            adapter = get_adapter(adapter_name)
            if adapter_name in ("surge", "loon"):
                content = adapter.export(proxies, washed_outbounds=washed_outbounds)
            else:
                content = adapter.export(proxies)
            out_path = output_dir / filename
            AtomicFileWriter.write_text(out_path, content)
            generated_files[key] = out_path
        except Exception as exc:
            logger.warning("Failed to generate %s output: %s", adapter_name, str(exc))

    # 3e. Side products pack (OpenVPN + WireGuard + plain URIs)
    side_products_path = output_dir / "side_products.zip"
    openvpn_candidates = [
        p for p in proxies if (p.protocol or "").lower() == "openvpn" and p.config
    ]
    wireguard_candidates = [
        p for p in proxies if (p.protocol or "").lower() in ("wireguard", "wg")
    ]
    if raw_content or openvpn_candidates or wireguard_candidates:
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=output_dir, prefix=".side_products.", suffix=".tmp", delete=False
            ) as tmp:
                tmp_path = tmp.name
            with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("proxies.txt", raw_content)
                for proxy in openvpn_candidates:
                    name = _safe_filename(
                        proxy.remarks or proxy.id, f"openvpn-{proxy.id[:8]}"
                    )
                    zf.writestr(f"openvpn/{name}.ovpn", proxy.config)
                for proxy in wireguard_candidates:
                    wg_config = _build_wireguard_config(proxy)
                    if not wg_config:
                        continue
                    name = _safe_filename(
                        proxy.remarks or proxy.id, f"wireguard-{proxy.id[:8]}"
                    )
                    zf.writestr(f"wireguard/{name}.conf", wg_config)
            os.replace(tmp_path, side_products_path)
            generated_files["side_products"] = side_products_path
        except Exception as exc:
            logger.warning("Failed to generate side_products.zip: %s", str(exc))
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    # 4. Categorized Sub-files (By Country & Protocol)
    # Grouping
    by_country: Dict[str, List[Proxy]] = {}
    by_protocol: Dict[str, List[Proxy]] = {}

    for p in proxies:
        if p.is_working:
            cc = (p.country_code or "XX").upper()
            by_country.setdefault(cc, []).append(p)
            by_protocol.setdefault((p.protocol or "").lower(), []).append(p)

    # Write Country files
    country_dir = output_dir / "countries"
    country_dir.mkdir(exist_ok=True)

    for cc, plist in by_country.items():
        # We generate files for all, including XX
        cpath = country_dir / f"{cc}.json"
        AtomicFileWriter.write_text(cpath, generate_singbox_config(plist))

        generated_files[f"country_{cc}"] = cpath

    # Write Protocol files
    proto_dir = output_dir / "protocols"
    proto_dir.mkdir(exist_ok=True)

    for proto, plist in by_protocol.items():
        ppath = proto_dir / f"{proto}.json"
        AtomicFileWriter.write_text(ppath, generate_singbox_config(plist))

        generated_files[f"proto_{proto}"] = ppath

    # 5. Chain-only output (Washed + Revived + Smart Chains + Shielded)
    # This includes ALL chain types: standard washed, revived (warp/vwarp), smart chains, and shielded (gold)
    chain_outbounds: List[Dict[str, Any]] = []
    seen_tags: set[str] = set()

    def _append_chain(outbounds: List[Dict[str, Any]]) -> None:
        for outbound in outbounds:
            if not isinstance(outbound, dict):
                continue
            tag = outbound.get("tag")
            if tag and tag in seen_tags:
                continue
            chain_outbounds.append(outbound)
            if tag:
                seen_tags.add(tag)

    # Include all chain types:
    # 1. Proxy-level chains (from revived proxies)
    for p in proxies:
        chain = p.details.get("chain_outbounds")
        if isinstance(chain, list) and chain:
            _append_chain(copy.deepcopy(chain))

    # 2. Washed outbounds (includes standard washed + shielded/gold chains)
    if washed_outbounds:
        _append_chain(copy.deepcopy(washed_outbounds))

    # 3. Smart chains
    if smart_chains:
        for chain_list in smart_chains.values():
            for chain in chain_list:
                if isinstance(chain, list) and chain:
                    _append_chain(copy.deepcopy(chain))

    if chain_outbounds:
        chains_config_content = generate_singbox_config(
            [], extra_outbounds=chain_outbounds
        )

        chains_path = output_dir / "singbox-chains.json"
        AtomicFileWriter.write_text(chains_path, chains_config_content)
        generated_files["singbox_chains"] = chains_path

        # [FIX] Alias: also save as chains.json if requested
        chains_alias_path = output_dir / "chains.json"
        AtomicFileWriter.write_text(chains_alias_path, chains_config_content)
        generated_files["chains"] = chains_alias_path

    # 5b. Separate outputs for different revival types (if needed for analytics)
    # Extract shielded (gold) chains separately for visibility
    shielded_chains: List[Dict[str, Any]] = []
    washed_only_chains: List[Dict[str, Any]] = []
    revived_only_chains: List[Dict[str, Any]] = []
    
    if washed_outbounds:
        for outbound in washed_outbounds:
            if not isinstance(outbound, dict):
                continue
            tag = outbound.get("tag", "")
            process = outbound.get("_process", "")
            
            # Shielded chains (GOLD- prefix or shield_payload process)
            if tag.startswith("GOLD-") or process == "shield_payload" or process == "shield_base":
                shielded_chains.append(copy.deepcopy(outbound))
            # Standard washed chains (not shielded)
            elif tag.startswith("🛡️") or process == "washed":
                washed_only_chains.append(copy.deepcopy(outbound))
    
    # Revived chains from proxy details
    for p in proxies:
        if p.details.get("is_revived") or (p.process or "").startswith("revived"):
            chain = p.details.get("chain_outbounds")
            if isinstance(chain, list) and chain:
                revived_only_chains.extend(copy.deepcopy(chain))
    
    # Generate separate outputs for analytics/debugging (optional, not user-facing)
    # These are kept for backward compatibility and internal tracking

    # 6. DNS-safe outputs (IP-only / pre-resolved)
    dns_safe_proxies, host_map = _build_dns_safe_proxies(proxies)
    if dns_safe_proxies:
        dns_safe_washed = (
            _filter_outbounds_for_dns_safe(washed_outbounds, host_map)
            if washed_outbounds
            else None
        )
        dns_safe_smart_chains: Dict[str, List[List[Dict[str, Any]]]] = {}
        if smart_chains:
            for group, chains in smart_chains.items():
                filtered_chains: List[List[Dict[str, Any]]] = []
                for chain in chains:
                    if not isinstance(chain, list):
                        continue
                    filtered = _filter_outbounds_for_dns_safe(chain, host_map)
                    if filtered:
                        filtered_chains.append(filtered)
                if filtered_chains:
                    dns_safe_smart_chains[group] = filtered_chains

        dns_split_files = generate_split_outputs(
            dns_safe_proxies,
            output_dir,
            washed_outbounds=dns_safe_washed,
            washed_ids=washed_ids,
            smart_chains=dns_safe_smart_chains,
            name_suffix="dns-safe",
            key_suffix="dns_safe",
        )
        generated_files.update(dns_split_files)

        dns_chain_outbounds: List[Dict[str, Any]] = []
        if chain_outbounds:
            dns_chain_outbounds = _filter_outbounds_for_dns_safe(
                chain_outbounds, host_map
            )
        if dns_chain_outbounds:
            dns_chains_content = generate_singbox_config(
                [], extra_outbounds=dns_chain_outbounds
            )
            dns_chains_path = output_dir / "singbox-chains-dns-safe.json"
            AtomicFileWriter.write_text(dns_chains_path, dns_chains_content)
            generated_files["singbox_chains_dns_safe"] = dns_chains_path

            dns_chains_alias = output_dir / "chains-dns-safe.json"
            AtomicFileWriter.write_text(dns_chains_alias, dns_chains_content)
            generated_files["chains_dns_safe"] = dns_chains_alias

        dns_safe_base64 = generate_base64_subscription(dns_safe_proxies)
        dns_base64_path = output_dir / "base64-dns-safe.txt"
        AtomicFileWriter.write_text(dns_base64_path, dns_safe_base64)
        generated_files["base64_dns_safe"] = dns_base64_path

        dns_raw_content = generate_plaintext_subscription(dns_safe_proxies)
        dns_proxies_txt_path = output_dir / "proxies-dns-safe.txt"
        AtomicFileWriter.write_text(dns_proxies_txt_path, dns_raw_content)
        generated_files["proxies_txt_dns_safe"] = dns_proxies_txt_path

        dns_chosen = _select_chosen_proxies(dns_safe_proxies)
        if dns_chosen:
            chosen_dir = output_dir / "chosen"
            chosen_dir.mkdir(exist_ok=True)
            chosen_dns_base64 = generate_base64_subscription(dns_chosen)
            chosen_dns_path = chosen_dir / "base64-dns-safe.txt"
            AtomicFileWriter.write_text(chosen_dns_path, chosen_dns_base64)
            generated_files["chosen_base64_dns_safe"] = chosen_dns_path

        # Adapter-specific outputs (DNS-safe)
        for key, (adapter_name, filename) in adapter_specs.items():
            try:
                adapter = get_adapter(adapter_name)
                if adapter_name in ("surge", "loon"):
                    content = adapter.export(dns_safe_proxies, washed_outbounds=dns_safe_washed)
                else:
                    content = adapter.export(dns_safe_proxies)
                dns_filename = _add_suffix(filename, "-dns-safe")
                out_path = output_dir / dns_filename
                AtomicFileWriter.write_text(out_path, content)
                generated_files[f"{key}_dns_safe"] = out_path
            except Exception as exc:
                logger.warning(
                    "Failed to generate dns-safe %s output: %s",
                    adapter_name,
                    str(exc),
                )

        # Side products pack (DNS-safe)
        side_dns_path = output_dir / "side_products-dns-safe.zip"
        openvpn_candidates_dns = [
            p
            for p in dns_safe_proxies
            if (p.protocol or "").lower() == "openvpn" and p.config
        ]
        wireguard_candidates_dns = [
            p for p in dns_safe_proxies if (p.protocol or "").lower() in ("wireguard", "wg")
        ]
        if dns_raw_content or openvpn_candidates_dns or wireguard_candidates_dns:
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    dir=output_dir, prefix=".side_products_dns.", suffix=".tmp", delete=False
                ) as tmp:
                    tmp_path = tmp.name
                with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr("proxies.txt", dns_raw_content)
                    for proxy in openvpn_candidates_dns:
                        original_host = proxy.details.get("original_host") or proxy.address
                        rewritten = _rewrite_openvpn_remote(proxy.config, original_host, proxy.address)
                        name = _safe_filename(
                            proxy.remarks or proxy.id, f"openvpn-{proxy.id[:8]}"
                        )
                        zf.writestr(f"openvpn/{name}.ovpn", rewritten)
                    for proxy in wireguard_candidates_dns:
                        wg_config = _build_wireguard_config(proxy)
                        if not wg_config:
                            continue
                        name = _safe_filename(
                            proxy.remarks or proxy.id, f"wireguard-{proxy.id[:8]}"
                        )
                        zf.writestr(f"wireguard/{name}.conf", wg_config)
                os.replace(tmp_path, side_dns_path)
                generated_files["side_products_dns_safe"] = side_dns_path
            except Exception as exc:
                logger.warning("Failed to generate side_products-dns-safe.zip: %s", str(exc))
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass

    # 7. DNS-hardened outputs (prefer IP when available + DoH/DoT/DoQ)
    if AppSettings().DNS_HARDENED_OUTPUTS:
        dns_hardened_proxies, hardened_map = _build_dns_hardened_proxies(proxies)
        if dns_hardened_proxies:
            primary_resolvers, fallback_resolvers = _dns_resolver_sets()
            hardened_washed = (
                _filter_outbounds_for_dns_hardened(washed_outbounds, hardened_map)
                if washed_outbounds
                else None
            )
            hardened_smart_chains: Dict[str, List[List[Dict[str, Any]]]] = {}
            if smart_chains:
                for group, chains in smart_chains.items():
                    filtered_chains: List[List[Dict[str, Any]]] = []
                    for chain in chains:
                        if not isinstance(chain, list):
                            continue
                        filtered = _filter_outbounds_for_dns_hardened(chain, hardened_map)
                        if filtered:
                            filtered_chains.append(filtered)
                    if filtered_chains:
                        hardened_smart_chains[group] = filtered_chains

            hardened_split_files = generate_split_outputs(
                dns_hardened_proxies,
                output_dir,
                washed_outbounds=hardened_washed,
                washed_ids=washed_ids,
                smart_chains=hardened_smart_chains,
                name_suffix="dns-hardened",
                key_suffix="dns_hardened",
                singbox_dns_profile=build_singbox_dns_profile(),
                clash_dns_profile=build_clash_dns_profile(),
            )
            generated_files.update(hardened_split_files)

            # Base64 + plaintext outputs (DNS-hardened prefer-IP)
            dns_hardened_base64 = generate_base64_subscription(dns_hardened_proxies)
            dns_hardened_base64_path = output_dir / "base64-dns-hardened.txt"
            AtomicFileWriter.write_text(dns_hardened_base64_path, dns_hardened_base64)
            generated_files["base64_dns_hardened"] = dns_hardened_base64_path

            dns_hardened_raw = generate_plaintext_subscription(dns_hardened_proxies)
            dns_hardened_txt_path = output_dir / "proxies-dns-hardened.txt"
            AtomicFileWriter.write_text(dns_hardened_txt_path, dns_hardened_raw)
            generated_files["proxies_txt_dns_hardened"] = dns_hardened_txt_path

            dns_hardened_chosen = _select_chosen_proxies(dns_hardened_proxies)
            if dns_hardened_chosen:
                chosen_dir = output_dir / "chosen"
                chosen_dir.mkdir(exist_ok=True)
                chosen_hardened_base64 = generate_base64_subscription(
                    dns_hardened_chosen
                )
                chosen_hardened_path = chosen_dir / "base64-dns-hardened.txt"
                AtomicFileWriter.write_text(
                    chosen_hardened_path, chosen_hardened_base64
                )
                generated_files["chosen_base64_dns_hardened"] = chosen_hardened_path

            # Adapter-specific outputs (DNS-hardened)
            try:
                shadowrocket_hardened = _wrap_shadowrocket_profile(
                    dns_hardened_proxies, primary_resolvers, fallback_resolvers
                )
                out_path = output_dir / "shadowrocket-dns-hardened.txt"
                AtomicFileWriter.write_text(out_path, shadowrocket_hardened)
                generated_files["shadowrocket_dns_hardened"] = out_path
            except Exception as exc:
                logger.warning("Failed to generate dns-hardened Shadowrocket: %s", exc)

            try:
                surge_hardened = _wrap_surge_or_loon_profile(
                    "surge",
                    dns_hardened_proxies,
                    hardened_washed,
                    primary_resolvers,
                    fallback_resolvers,
                )
                out_path = output_dir / "surge-dns-hardened.conf"
                AtomicFileWriter.write_text(out_path, surge_hardened)
                generated_files["surge_dns_hardened"] = out_path
            except Exception as exc:
                logger.warning("Failed to generate dns-hardened Surge: %s", exc)

            try:
                loon_hardened = _wrap_surge_or_loon_profile(
                    "loon",
                    dns_hardened_proxies,
                    hardened_washed,
                    primary_resolvers,
                    fallback_resolvers,
                )
                out_path = output_dir / "loon-dns-hardened.conf"
                AtomicFileWriter.write_text(out_path, loon_hardened)
                generated_files["loon_dns_hardened"] = out_path
            except Exception as exc:
                logger.warning("Failed to generate dns-hardened Loon: %s", exc)

            try:
                quantumult_hardened = _wrap_quantumultx_profile(
                    dns_hardened_proxies, primary_resolvers, fallback_resolvers
                )
                out_path = output_dir / "quantumult-dns-hardened.conf"
                AtomicFileWriter.write_text(out_path, quantumult_hardened)
                generated_files["quantumult_dns_hardened"] = out_path
            except Exception as exc:
                logger.warning("Failed to generate dns-hardened Quantumult X: %s", exc)

            try:
                sip_adapter = get_adapter("sip008")
                sip_content = sip_adapter.export(dns_hardened_proxies)
                sip_path = output_dir / "sip008-dns-hardened.json"
                AtomicFileWriter.write_text(sip_path, sip_content)
                generated_files["sip008_dns_hardened"] = sip_path
            except Exception as exc:
                logger.warning("Failed to generate dns-hardened SIP008: %s", exc)

            # Side products pack (DNS-hardened)
            side_hardened_path = output_dir / "side_products-dns-hardened.zip"
            openvpn_hardened = [
                p
                for p in dns_hardened_proxies
                if (p.protocol or "").lower() == "openvpn" and p.config
            ]
            wireguard_hardened = [
                p
                for p in dns_hardened_proxies
                if (p.protocol or "").lower() in ("wireguard", "wg")
            ]
            if dns_hardened_raw or openvpn_hardened or wireguard_hardened:
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(
                        dir=output_dir,
                        prefix=".side_products_dns_hardened.",
                        suffix=".tmp",
                        delete=False,
                    ) as tmp:
                        tmp_path = tmp.name
                    with zipfile.ZipFile(
                        tmp_path, "w", compression=zipfile.ZIP_DEFLATED
                    ) as zf:
                        zf.writestr("proxies.txt", dns_hardened_raw)
                        for proxy in openvpn_hardened:
                            original_host = (
                                proxy.details.get("original_host") or proxy.address
                            )
                            rewritten = _rewrite_openvpn_remote(
                                proxy.config, original_host, proxy.address
                            )
                            name = _safe_filename(
                                proxy.remarks or proxy.id, f"openvpn-{proxy.id[:8]}"
                            )
                            zf.writestr(f"openvpn/{name}.ovpn", rewritten)
                        for proxy in wireguard_hardened:
                            wg_config = _build_wireguard_config(proxy)
                            if not wg_config:
                                continue
                            name = _safe_filename(
                                proxy.remarks or proxy.id, f"wireguard-{proxy.id[:8]}"
                            )
                            zf.writestr(f"wireguard/{name}.conf", wg_config)
                    os.replace(tmp_path, side_hardened_path)
                    generated_files["side_products_dns_hardened"] = side_hardened_path
                except Exception as exc:
                    logger.warning(
                        "Failed to generate side_products-dns-hardened.zip: %s", exc
                    )
                    if tmp_path and os.path.exists(tmp_path):
                        try:
                            os.unlink(tmp_path)
                        except OSError:
                            pass

            # DNS-hardened chains (includes all chain types: washed, revived, smart, shielded)
            hardened_chain_outbounds: List[Dict[str, Any]] = []
            if chain_outbounds:
                hardened_chain_outbounds = _filter_outbounds_for_dns_hardened(
                    chain_outbounds, hardened_map
                )
            if hardened_chain_outbounds:
                hardened_chains_content = generate_singbox_config(
                    [], extra_outbounds=hardened_chain_outbounds
                )
                hardened_chains_path = output_dir / "singbox-chains-dns-hardened.json"
                AtomicFileWriter.write_text(hardened_chains_path, hardened_chains_content)
                generated_files["singbox_chains_dns_hardened"] = hardened_chains_path

                hardened_chains_alias = output_dir / "chains-dns-hardened.json"
                AtomicFileWriter.write_text(hardened_chains_alias, hardened_chains_content)
                generated_files["chains_dns_hardened"] = hardened_chains_alias

    # 8. Legacy compatibility: Ensure all legacy outputs are preserved
    # These are already generated above, but we verify they exist for backward compatibility
    legacy_required = [
        "base64",
        "singbox",
        "clash",
        "shadowrocket",
        "surge",
        "loon",
        "quantumult",
        "sip008",
    ]
    for legacy_key in legacy_required:
        if legacy_key not in generated_files:
            logger.warning(f"Legacy output '{legacy_key}' not generated - may break compatibility")

    logger.info(f"Generated {len(generated_files)} output files (including all variations).")
    return generated_files


def save_metadata(
    stats: Any,
    proxies: List[Proxy],
    output_dir: Path,
):
    """
    Saves metadata.json and other stats files.
    """
    meta_path = output_dir / "metadata.json"

    # Single-pass loop to collect all stats at once (O(N) instead of O(4N))
    total = len(proxies)
    working = 0
    lat_dist = {"fast": 0, "medium": 0, "slow": 0, "very_slow": 0}
    protocols: Dict[str, int] = {}
    countries: Dict[str, int] = {}
    asns: Dict[str, int] = {}
    latency_by_country_sum: Dict[str, float] = {}
    latency_by_country_count: Dict[str, int] = {}
    latency_by_protocol_sum: Dict[str, float] = {}
    latency_by_protocol_count: Dict[str, int] = {}

    for p in proxies:
        if not p.is_working:
            continue

        working += 1

        # Latency distribution
        latency = p.latency or 9999
        if latency < 200:
            lat_dist["fast"] += 1
        elif latency < 800:
            lat_dist["medium"] += 1
        elif latency < 2000:
            lat_dist["slow"] += 1
        else:
            lat_dist["very_slow"] += 1

        # Protocol count
        protocols[p.protocol] = protocols.get(p.protocol, 0) + 1

        # Country count
        cc = p.country_code if p.country_code else "XX"
        countries[cc] = countries.get(cc, 0) + 1

        # Latency by country/protocol (avg)
        if p.latency is not None:
            latency_by_country_sum[cc] = latency_by_country_sum.get(cc, 0.0) + p.latency
            latency_by_country_count[cc] = latency_by_country_count.get(cc, 0) + 1
            proto_key = p.protocol or "unknown"
            latency_by_protocol_sum[proto_key] = (
                latency_by_protocol_sum.get(proto_key, 0.0) + p.latency
            )
            latency_by_protocol_count[proto_key] = (
                latency_by_protocol_count.get(proto_key, 0) + 1
            )

        # ASN count
        if p.asn:
            asns[p.asn] = asns.get(p.asn, 0) + 1

        # Note: Heuristic counts removed - use exact counts from PipelineStats instead
        # (revived_warp, revived_vwarp, washer_success_count)

    # Extract info from stats (dict or object)
    total_sourced = total
    parsed_count = total
    tested_count = total
    reasons: Dict[str, int] = {}
    end_time_iso = datetime.now(timezone.utc).isoformat()
    washed_count = 0
    smart_chain_count = 0
    vwarp_win_rate = 0.0
    scanner_ips_found = 0
    fetched_sources = 0
    total_configured_sources = 0  # Total sources from config for frontend display
    # Additional stats that were missing from export
    revived_warp = 0
    revived_vwarp = 0
    vwarp_attempts = 0
    vwarp_success = 0
    duration_seconds = 0.0
    geo_resolved = 0
    cache_misses = 0
    final_count = 0
    chain_outbounds_count = 0
    time_limited = False
    time_limit_seconds = 0

    if isinstance(stats, dict):
        # Stats is a dict (from merge script)
        total_sourced = safe_int_conversion(
            stats.get("fetched_lines") or stats.get("total_fetched") or total
        )
        parsed_count = stats.get("parsed", total)
        tested_count = stats.get("tested", total)
        # reasons might be in stats['rejection_reasons'] or stats['drop_reasons']
        raw_reasons = stats.get("rejection_reasons") or stats.get("drop_reasons") or {}
        if isinstance(raw_reasons, dict):
            reasons = {
                str(k): safe_int_conversion(v)
                for k, v in raw_reasons.items()
                if k is not None
            }
        washed_count = stats.get("washed_chains") or stats.get(
            "washer_success_count", 0
        )
        smart_chain_count = stats.get("smart_chain_count", 0)
        if not smart_chain_count and "smart_chains_breakdown" in stats:
            smart_chain_count = sum(stats["smart_chains_breakdown"].values())
        vwarp_win_rate = stats.get("vwarp_win_rate", 0.0)
        scanner_ips_found = stats.get("scanner_ips_found", 0)
        fetched_sources = stats.get("fetched_sources", 0)
        total_configured_sources = (
            stats.get("total_configured_sources", 0) or fetched_sources
        )
        # Extract additional stats from dict
        revived_warp = stats.get("revived_warp", 0)
        revived_vwarp = stats.get("revived_vwarp", 0)
        vwarp_attempts = stats.get("vwarp_attempts", 0)
        vwarp_success = stats.get("vwarp_success", 0)
        duration_seconds = stats.get("duration", 0.0)
        geo_resolved = stats.get("geo_resolved", 0)
        cache_misses = stats.get("cache_misses", 0)
        final_count = stats.get("final_count", 0)
        chain_outbounds_count = stats.get("chain_outbounds_count", 0)
        time_limited = bool(stats.get("time_limited", False))
        time_limit_seconds = int(stats.get("time_limit_seconds", 0) or 0)
    else:
        # Stats is an object (PipelineStats)
        if hasattr(stats, "fetched_lines"):
            total_sourced = stats.fetched_lines
        elif hasattr(stats, "total_sourced"):
            total_sourced = stats.total_sourced
        if hasattr(stats, "parsed"):
            parsed_count = stats.parsed
        if hasattr(stats, "tested"):
            tested_count = stats.tested
        if hasattr(stats, "drop_reasons"):
            reasons = stats.drop_reasons
        if hasattr(stats, "end_time") and stats.end_time:
            end_time_iso = stats.end_time.isoformat()
        if hasattr(stats, "washer_success_count"):
            washed_count = stats.washer_success_count
        if hasattr(stats, "smart_chain_count"):
            smart_chain_count = stats.smart_chain_count
        if hasattr(stats, "vwarp_win_rate"):
            vwarp_win_rate = stats.vwarp_win_rate
        if hasattr(stats, "scanner_ips_found"):
            scanner_ips_found = stats.scanner_ips_found
        if hasattr(stats, "fetched_sources"):
            fetched_sources = stats.fetched_sources
        # Extract total_configured_sources for frontend sources_count
        if hasattr(stats, "total_configured_sources"):
            total_configured_sources = stats.total_configured_sources or fetched_sources
        # Extract additional stats from PipelineStats object
        if hasattr(stats, "revived_warp"):
            revived_warp = stats.revived_warp
        if hasattr(stats, "revived_vwarp"):
            revived_vwarp = stats.revived_vwarp
        if hasattr(stats, "vwarp_attempts"):
            vwarp_attempts = stats.vwarp_attempts
        if hasattr(stats, "vwarp_success"):
            vwarp_success = stats.vwarp_success
        if hasattr(stats, "duration"):
            duration_seconds = stats.duration
        if hasattr(stats, "geo_resolved"):
            geo_resolved = stats.geo_resolved
        if hasattr(stats, "cache_misses"):
            cache_misses = stats.cache_misses
        if hasattr(stats, "final_count"):
            final_count = stats.final_count
        if hasattr(stats, "chain_outbounds_count"):
            chain_outbounds_count = stats.chain_outbounds_count
        if hasattr(stats, "time_limited"):
            time_limited = bool(stats.time_limited)
        if hasattr(stats, "time_limit_seconds"):
            time_limit_seconds = int(stats.time_limit_seconds or 0)
        # Use stats.working as source of truth (more accurate than counting in loop)
        if hasattr(stats, "working"):
            working = stats.working

    # Use stats.working if available (more accurate than loop count)
    if isinstance(stats, dict):
        working = stats.get("working", working)

    # Note: Removed heuristic fallbacks - use exact counts from PipelineStats
    # If counts are 0, they should remain 0 (not estimated from tags)

    # Separation of Smart Chains
    smart_chains_breakdown = {}
    if isinstance(stats, dict) and "smart_chains_breakdown" in stats:
        smart_chains_breakdown = stats["smart_chains_breakdown"]

    try:
        pkg_version = version("configstream")
    except Exception:
        pkg_version = "unknown"

    # Calculate update interval (default 6 hours for production)
    update_interval_hours = AppSettings().UPDATE_INTERVAL_HOURS

    latency_by_country = {
        cc: round(latency_by_country_sum[cc] / latency_by_country_count[cc])
        for cc in latency_by_country_sum
        if latency_by_country_count.get(cc)
    }
    latency_by_protocol = {
        proto: round(latency_by_protocol_sum[proto] / latency_by_protocol_count[proto])
        for proto in latency_by_protocol_sum
        if latency_by_protocol_count.get(proto)
    }

    # Compute total_revived from exact counts (no heuristics)
    # Use PipelineStats.total_revived property if available, otherwise calculate
    if isinstance(stats, dict):
        total_revived_count = stats.get("total_revived", revived_warp + revived_vwarp)
    else:
        if hasattr(stats, "total_revived"):
            total_revived_count = stats.total_revived
        else:
            total_revived_count = revived_warp + revived_vwarp

    # Washing Enabled Logic (Best effort inference for Shards)
    washing_enabled = False
    warp_pool_raw = AppSettings().WARP_KEY_POOL
    if isinstance(warp_pool_raw, str) and warp_pool_raw.strip():
        try:
            warp_pool = json.loads(warp_pool_raw)
            washing_enabled = isinstance(warp_pool, list) and len(warp_pool) > 0
        except json.JSONDecodeError:
            # Non-JSON value treated as enabled if non-empty (backward compat)
            washing_enabled = True
    washing_enabled = washing_enabled or vwarp_attempts > 0

    meta = {
        "schema_version": "2.3.0",  # Updated to match generators.py
        "version": pkg_version,
        "total_proxies": total + smart_chain_count,  # Working proxies + smart chains
        "total_tested": tested_count,  # Number of proxies actually tested
        "total_working": working,
        "success_rate": (working / tested_count) if tested_count > 0 else 0,
        "generated_at": end_time_iso,
        "last_updated_utc": end_time_iso,
        "latency_distribution": lat_dist,
        "protocols": protocols,
        "country_stats": countries,
        "countries": countries,  # Backward compatibility for statistics.js
        "rejection_reasons": reasons,
        "asns": asns,
        "isp_stats": asns,  # Alias for legacy tests
        "total_revived": total_revived_count,
        "total_smart_chains": smart_chain_count,
        "smart_chains_breakdown": smart_chains_breakdown,
        "total_dirty": sum(
            [
                int(reasons.get("dirty_ip", 0) or 0),
                int(reasons.get("DIRTY_IP", 0) or 0),
                int(reasons.get("honeypot", 0) or 0),
                int(reasons.get("HONEYPOT", 0) or 0),
            ]
        ),
        # Intelligence Layer Stats (canonical keys used by frontend)
        "vwarp_win_rate": vwarp_win_rate,
        "scanner_ips_found": scanner_ips_found,
        "washer_success_count": washed_count,
        "smart_chain_count": smart_chain_count,
        "chain_outbounds_count": chain_outbounds_count,
        # Export all revive/vwarp stats for complete tracking
        "revived_warp": revived_warp,
        "revived_vwarp": revived_vwarp,
        "vwarp_attempts": vwarp_attempts,
        "vwarp_success": vwarp_success,
        "washing_enabled": washing_enabled,
        # Export pipeline performance metrics
        "duration_seconds": duration_seconds,
        "geo_resolved": geo_resolved,
        "cache_misses": cache_misses,
        "final_count": final_count or working,
        "time_limited": time_limited,
        "time_limit_seconds": time_limit_seconds,
        # Canonical Keys (Consolidated)
        "total_lines_sourced": total_sourced,
        "total_unique_candidates": parsed_count,  # Parsed proxies (before testing)
        "total_valid_proxies": working,
        # Source counts - consolidated to avoid redundancy
        # Primary field: total_configured_sources (total sources in config)
        # Secondary field: fetched_sources (actual sources processed)
        "total_configured_sources": total_configured_sources or fetched_sources,
        "fetched_sources": fetched_sources,  # Actual sources processed
        # Legacy aliases for backward compatibility (deprecated, use total_configured_sources)
        "sources_count": total_configured_sources or fetched_sources,
        "total_sources": total_configured_sources or fetched_sources,
        "update_interval_hours": update_interval_hours,
        "latency_by_country": latency_by_country,
        "latency_by_protocol": latency_by_protocol,
        # Legacy mappings for backward compatibility (tests only)
        "fetched_lines": total_sourced,
        "parsed": parsed_count,
        "tested": tested_count,
        "working": working,
        # [FIX] Added chosen_subset_size for transparency
        "chosen_subset_size": len(_select_chosen_proxies(proxies)),
    }

    AtomicFileWriter.write_text(
        meta_path, json.dumps(meta, indent=2, ensure_ascii=False)
    )

    # NOTE: statistics.json removed - metadata.json is now single source of truth
    # All frontend code updated to use metadata.json directly
